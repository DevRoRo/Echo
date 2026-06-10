# Implementação LTI 1.3 no Echo: Uma Análise Arquitetural

## Introdução

O Echo é um backend FastAPI para geração de áudio por IA, projetado para integrar-se ao Moodle como uma ferramenta externa via LTI (Learning Tools Interoperability) versão 1.3. Este ensaio analisa a implementação dessa integração sob a ótica da arquitetura hexagonal (ports & adapters), explorando as decisões de design, os desafios encontrados e as soluções adotadas para conectar dois ecossistemas distintos — o Moodle como plataforma de aprendizagem e o Echo como ferramenta de áudio — de forma segura, extensível e desacoplada.

O LTI 1.3 é construído sobre OAuth 2.0 e OpenID Connect. Diferentemente de versões anteriores, ele exige que a ferramenta (Echo) valide JWTs assinados pela plataforma (Moodle), verificando a identidade do usuário e o contexto do curso sem depender de segredos compartilhados. Essa mudança traz complexidade criptográfica, mas também abre espaço para um design mais limpo e seguro.

---

## 1. A Arquitetura Hexagonal como Fundação

O Echo já nasceu hexagonal. O código está organizado em três círculos concêntricos:

1. **Núcleo (`core/`)** — contém os modelos de domínio, as portas de entrada (inbound ports) e saída (outbound ports), e os casos de uso. Nenhuma dependência externa — apenas Python puro e bibliotecas padrão.
2. **Adaptadores de entrada (driving adapters)** — `adapters/lti_router.py` (endpoints FastAPI) e `adapters/lti_middleware.py` (middleware Starlette). Traduzem requisições HTTP em chamadas aos casos de uso.
3. **Adaptadores de saída (driven adapters)** — `adapters/lti_repository.py` (SQLite via SQLAlchemy), `adapters/lti_key_manager.py` (geração de chaves RSA via `cryptography`), e `adapters/lti_pylti1p3_adapter.py` (wrappers para a biblioteca `pylti1p3`).

A integração LTI estende esse padrão naturalmente. Cada novo componente se encaixa em uma camada preexistente, sem violar as fronteiras arquiteturais.

---

## 2. Modelos de Domínio e Portas

Dois modelos de domínio foram introduzidos:

- **`PlatformRegistration`** — representa o registro de uma plataforma (Moodle) que pode lançar o Echo. Contém `issuer` (URL do Moodle), `client_id`, `auth_login_url`, `auth_token_url`, `auth_keyset_url` (endpoint JWKS do Moodle) e `deployment_ids` (um ou mais IDs de implantação).
- **`LtiSession`** — representa uma sessão OIDC transitória, identificada por um `nonce` (UUID), com validade de 5 minutos. Usada para rastrear o estado do fluxo de login.

As portas de saída — `PlatformRepositoryPort` e `LtiSessionRepositoryPort` — definem contratos para persistência. As portas de entrada — `RegisterPlatformUseCasePort`, `ListPlatformsUseCasePort`, `DeletePlatformUseCasePort`, `InitiateLoginUseCasePort` e `ValidateLaunchUseCasePort` — definem as operações que o mundo exterior pode realizar no núcleo.

O design é notavelmente enxuto: cada porta tem exatamente um método `execute()`, e cada caso de uso tem uma única responsabilidade. Isso torna o sistema fácil de testar, estender e depurar.

---

## 3. O Padrão de Adaptação do pylti1p3

A biblioteca `pylti1p3` foi projetada para Flask e Django. Ela espera objetos de requisição específicos desses frameworks, lida com cookies de sessão e gerencia estado OIDC via cache. A decisão arquitetural central foi: *como adaptar o pylti1p3 para FastAPI sem reescrever a lógica de validação de JWT?*

A resposta veio em quatro classes, cada uma resolvendo um problema específico:

### 3.1 `DbToolConf(ToolConfAbstract)`

O pylti1p3 usa `ToolConfAbstract` para buscar configurações de registro (URLs, chaves, client IDs). A implementação padrão usa dicionários estáticos. `DbToolConf` substitui isso por consultas ao banco SQLite via `PlatformRepositoryPort`. Cada plataforma Moodle registrada é convertida para um objeto `Registration` do pylti1p3 usando o padrão builder:

```python
reg = Registration()
reg.set_issuer(platform.issuer)
reg.set_client_id(platform.client_id)
reg.set_auth_login_url(platform.auth_login_url)
reg.set_key_set_url(platform.auth_keyset_url)
reg.set_tool_private_key(self._private_key)
```

A chamada `set_iss_has_one_client("*")` no construtor simplifica o modelo de configuração, informando ao pylti1p3 que qualquer emissor tem exatamente um client ID — o que é verdade para uma instância Echo servindo um único Moodle.

### 3.2 `FastAPIMessageLaunch(MessageLaunch)`

`MessageLaunch` é a classe central de validação do pylti1p3. Ela espera extrair parâmetros (`id_token`, `state`) de uma requisição Flask. A solução foi **subclasseá-la** e sobrescrever o único método abstrato `_get_request_param(key)`:

```python
class FastAPIMessageLaunch(MessageLaunch):
    def __init__(self, id_token: str, state: str, tool_config: ToolConfAbstract):
        self._params = {"id_token": id_token, "state": state}
        super().__init__(request=self, tool_config=tool_config,
                         session_service=StubSessionService(),
                         cookie_service=StubCookieService())

    def _get_request_param(self, key: str) -> str:
        return self._params[key]
```

O objeto se passa por requisição (`request=self`), redirecionando a leitura de parâmetros para um dicionário local. Isso elimina a necessidade de qualquer objeto de requisição Flask — uma ponte elegante de 10 linhas.

### 3.3 `StubSessionService` e `StubCookieService`

O `MessageLaunch` exige `session_service` e `cookie_service` em seu construtor. O `SessionService` padrão verifica state e nonce na sessão; o `CookieService` padrão gerencia cookies. Como o Echo já valida state e nonce manualmente no `ValidateLaunchUseCase` (antes de chamar o pylti1p3), e não usa cookies para sessão (usa JWTs stateless), esses serviços são substituídos por stubs:

- `StubSessionService.check_state_is_valid()` → retorna `True`
- `StubSessionService.check_nonce()` → retorna `True`
- `StubCookieService.get_cookie()` → retorna `None`
- `StubCookieService.set_cookie()` → no-op

Essa abordagem segue o princípio de *segregação de interfaces*: em vez de forçar o Echo a adotar o modelo de sessão/cookies do pylti1p3, criamos implementações mínimas que satisfazem o contrato sem adicionar complexidade.

### 3.4 Por que não usar OIDCLogin?

O `OIDCLogin` do pylti1p3 gerencia o fluxo de login OIDC — gera nonce, constrói a URL de autenticação, lida com cookies. Mas ele é fortemente acoplado a Flask (espera objetos `Request` e `Response`). Em vez de adaptá-lo, optou-se por uma implementação manual de ~35 linhas no `InitiateLoginUseCase`:

1. Busca o `PlatformRegistration` pelo `issuer`.
2. Gera um nonce (`uuid.uuid4().hex`).
3. Salva um `LtiSession` com validade de 5 minutos.
4. Constrói a URL de autorização do Moodle com `response_type=id_token`, `scope=openid`, `response_mode=form_post`, `client_id`, `redirect_uri`, `state`, `nonce`, `login_hint`.
5. Retorna a URL de redirecionamento.

A simplicidade dessa abordagem contrasta com a complexidade de adaptar o `OIDCLogin`. É uma vitória do design hexagonal: a lógica de negócio fica pura e testável, enquanto o redirecionamento HTTP é tratado pelo adaptador (`lti_router.py`).

---

## 4. Sessão Stateless via JWT

Após um lançamento bem-sucedido, o Echo não cria sessão no servidor. Em vez disso, emite um **JWT stateless** assinado com sua própria chave RSA privada, contendo:

- `sub` — ID do usuário no Moodle
- `name`, `email` — dados do usuário
- `roles` — papéis (Instructor, Student, etc.)
- `course_id`, `course_title` — contexto do curso
- `resource_link_id` — identificador do link da ferramenta
- `exp` — timestamp de expiração

O middleware `LTIAuthMiddleware` valida esse JWT em cada requisição usando a chave pública do Echo:

```python
payload = jwt_decode(token, public_key_pem, algorithms=["RS256"])
```

**Nenhuma consulta ao banco de dados é necessária para autenticação.** O sistema é totalmente stateless: escalável, simples e resiliente. O JWT carrega toda a informação necessária para autorizar a requisição, incluindo o contexto do curso — o que permite que o Echo escute requisições por usuário e por curso sem consultar o Moodle.

---

## 5. Fluxo Ponta a Ponta

O fluxo completo de lançamento LTI 1.3 entre Moodle e Echo segue seis passos:

**Passo 1 — Iniciação do Login OIDC:** O usuário clica no link da ferramenta Echo no Moodle. O Moodle envia um `POST /lti/login/` com `iss`, `target_link_uri`, `login_hint` e `lti_message_hint` como campos de formulário.

**Passo 2 — Redirecionamento para Autenticação:** O `InitiateLoginUseCase` busca o registro da plataforma, gera um nonce, salva um `LtiSession`, e redireciona o usuário para o endpoint OIDC do Moodle com `state=nonce` e outros parâmetros.

**Passo 3 — Autenticação no Moodle:** O usuário autentica-se no Moodle (tipicamente de forma transparente, pois já está logado). O Moodle então envia um `POST /lti/launch/` com `id_token=<JWT>` e `state=<nonce>`.

**Passo 4 — Validação do JWT:** O `ValidateLaunchUseCase` busca o `LtiSession` pelo nonce, verifica se não expirou, constrói um `DbToolConf`, cria um `FastAPIMessageLaunch`, e chama `launch.validate()`. O pylti1p3 baixa a JWKS do Moodle, verifica a assinatura do JWT, valida `aud`, `iss`, `exp`, `nonce`, e confirma o deployment.

**Passo 5 — Emissão do Token de Sessão:** O caso de uso extrai as claims do JWT validado, deleta o `LtiSession` (uso único), e emite um novo JWT assinado pelo Echo com os dados do usuário e contexto do curso. Redireciona o navegador para o frontend com `session_token=<JWT>`.

**Passo 6 — Requisições Autenticadas:** O frontend armazena o session token e o envia em toda requisição como `Authorization: Bearer <JWT>`. O `LTIAuthMiddleware` valida a assinatura em cada requisição — sem banco de dados, sem estado, sem latência.

---

## 6. Desafios e Correções

### 6.1 Query vs. Form

O primeiro erro foi sutil: a implementação inicial usava `Query(...)` para extrair `id_token` e `state` no endpoint `/lti/launch/`. O problema é que o LTI 1.3 usa `response_mode=form_post`, o que significa que o Moodle envia esses valores como campos de formulário (`application/x-www-form-urlencoded`), não como parâmetros de URL. O FastAPI com `Query()` retornaria 422.

O mesmo problema se repetiu no endpoint `/lti/login/`, que inicialmente era `GET` com `Query()` — mas o Moodle envia um `POST` com formulário. A correção envolveu:

1. Mudar `Query(...)` para `Form(...)` em ambos os endpoints.
2. Mudar `@router.get("/login/")` para `@router.post("/login/")` e `@router.post("/login")`.
3. Adicionar a rota sem barra final (`/login`) para evitar o redirecionamento 307 do FastAPI, que converteria o POST em GET e perderia o corpo da requisição.

### 6.2 O Construtor do Deployment

Outro erro revelou a importância de conhecer a API real das bibliotecas: o código criava `Deployment(iss, deployment_id)`, mas a classe `Deployment` do pylti1p3 2.0.0 tem um construtor sem parâmetros. O único método disponível é `set_deployment_id()`. A correção:

```python
dep = Deployment()
dep.set_deployment_id(deployment_id)
```

Esse erro ilustra um risco comum em integrações: assumir que uma API é mais rica do que realmente é. A leitura atenta da fonte da biblioteca (13 linhas) teria evitado o problema.

### 6.3 A Complexidade Acidental do GET/POST

O problema do `GET` vs `POST` no `/lti/login/` não era apenas técnico — era conceitual. O desenvolvedor associou mentalmente "login initiation" a "GET" (porque o resultado é um redirect), mas o LTI 1.3 define a iniciação como um POST da plataforma para a ferramenta. A distinção é sutil, mas crucial: o método HTTP reflete quem inicia a comunicação (a plataforma), não o resultado final (o redirect).

---

## 7. Gerenciamento de Chaves

O Echo gera um par de chaves RSA-2048 na primeira execução, armazenando-as em `keys/private.key` e `keys/public.key`. A classe `LtiKeyManager` é o adaptador que:

- Gera as chaves via `cryptography.hazmat.primitives.asymmetric.rsa`.
- Converte a chave pública para formato JWK via `jwcrypto.jwk` (para o endpoint `/lti/jwks`).
- Disponibiliza as chaves em PEM para assinatura (privada) e validação (pública).

O endpoint `/lti/jwks` expõe a chave pública no formato padrão JWK Set, consumido pelo Moodle para verificar as assinaturas dos JWTs emitidos pelo Echo durante o fluxo de sessão. O Echo também consome o JWKS do Moodle (via `auth_keyset_url`) para validar o `id_token` recebido no launch.

---

## 8. Configuração e Injeção de Dependência

A configuração usa `pydantic-settings` com prefixo `LTI_`:

```python
class LTISettings(BaseSettings):
    tool_name: str = "Echo"
    launch_url: str = "http://localhost:8000/lti/launch/..."
    session_token_expiry_seconds: int = 3600
```

A injeção de dependência é feita via variáveis globais de módulo em `adapters/dependencies.py`. `main.py` instancia os repositórios e casos de uso, atribuindo-os a essas variáveis. Os endpoints usam `Depends(get_*_use_case)` para obtê-los.

O padrão é simples e suficiente para um servidor single-process. Embora não seja thread-safe em cenários de concorrência intensa, atende bem ao caso de uso: uma instância Echo servindo algumas dezenas de requisições simultâneas.

---

## 9. Os Sete Endpoints

| Método | Rota | Propósito |
|--------|------|-----------|
| `GET` | `/lti/config.json` | JSON de configuração para registro no Moodle |
| `GET` | `/lti/jwks` | Chave pública do Echo em formato JWK Set |
| `POST` | `/lti/login/` (e `/lti/login`) | Iniciação do login OIDC |
| `POST` | `/lti/launch/` | Validação do JWT e emissão do token de sessão |
| `POST` | `/lti/register/` | Registro de uma plataforma Moodle |
| `GET` | `/lti/registrations/` | Listagem de plataformas registradas |
| `DELETE` | `/lti/registrations/{id}` | Remoção de um registro |

Todos os endpoints LTI são públicos — não passam pelo `LTIAuthMiddleware` — pois fazem parte do próprio fluxo de autenticação.

---

## 10. Considerações sobre Testabilidade

A arquitetura hexagonal torna os casos de uso naturalmente testáveis. Cada caso de uso recebe suas dependências por injeção, e as portas são interfaces abstratas. Para testar o `ValidateLaunchUseCase`, por exemplo, basta mockar `PlatformRepositoryPort`, `LtiSessionRepositoryPort` e `LtiKeyManager` — sem necessidade de banco de dados, servidor HTTP ou chaves reais.

Os testes existentes (25 no total, todos passando) cobrem os repositórios SQLite e os casos de uso de áudio. A camada LTI aguarda testes próprios, mas a estrutura está pronta: as portas estão definidas, os casos de uso são puros, e os adaptadores são isolados.

---

## 11. Conclusão

A implementação do LTI 1.3 no Echo demonstra como uma arquitetura bem estruturada absorve complexidade sem se deformar. A camada hexagonal existente acomodou os novos componentes sem violar suas fronteiras: modelos de domínio enxutos, portas claras, casos de uso puros e adaptadores especializados.

A integração com o pylti1p3 — uma biblioteca projetada para outro ecossistema — foi resolvida não com forks ou workarounds, mas com subclassificação estratégica e stubs mínimos. O `FastAPIMessageLaunch` é um exemplo de adaptação elegante: 10 linhas que transformam uma classe Flask em uma classe FastAPI.

A decisão de não usar `OIDCLogin` e implementar o fluxo manualmente foi acertada. O resultado é mais simples, mais testável e mais alinhado com o estilo do FastAPI. A sessão stateless via JWT elimina a necessidade de armazenamento de sessão no servidor, tornando o Echo escalável por design.

Os bugs corrigidos — `Query` vs `Form`, `GET` vs `POST`, `Deployment(...)` vs `Deployment()` — são lições valiosas sobre os detalhes do protocolo LTI 1.3 e as idiossincrasias das bibliotecas. Cada correção fortaleceu o entendimento do sistema.

No fim, o Echo não é apenas uma ferramenta de áudio que "funciona com o Moodle". É um exemplo de como integrar dois sistemas complexos respeitando os princípios de design de software: separação de concerns, injeção de dependência, adaptação de interfaces e testeabilidade. O LTI 1.3, com sua complexidade criptográfica e protocolar, serviu como um excelente teste de estresse para a arquitetura — e ela passou.
