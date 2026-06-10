# LTI Launch Flow Diagram

This document contains the PlantUML sequence diagram for the LTI 1.3 launch flow between Moodle (Platform) and Echo (Tool).

## Diagram

```plantuml
@startuml LTI Launch Flow
' LTI 1.3 Launch Flow — Echo (Tool) + Moodle (Platform)

actor "User\n(Browser)" as User
participant "Moodle\n(Platform)" as Moodle
participant "Echo Backend\n(FastAPI)" as Echo
database "Echo DB\n(SQLite)" as DB
participant "Echo Frontend\n(React)" as Frontend

== Step 1: OIDC Login Initiation ==

User -> Moodle: Clicks Echo tool link in course
Moodle -> Echo: POST /lti/login/\niss, target_link_uri, login_hint, lti_message_hint
activate Echo
Echo -> DB: Find PlatformRegistration by issuer
DB --> Echo: PlatformRegistration
Echo -> DB: Generate nonce, save LtiSession
note right: nonce = uuid4().hex\nexpires in 5 minutes
Echo --> Moodle: 302 Redirect to Moodle's OIDC auth endpoint\n(with state=nonce, nonce, client_id, redirect_uri)
deactivate Echo

== Step 2: Authentication at Moodle ==

Moodle -> User: Redirect to Moodle login page
User -> Moodle: Authenticates (seamless if session active)
note right: User is typically\nalready logged into Moodle

== Step 3: LTI Launch ==

Moodle -> Echo: POST /lti/launch/\nid_token=<LTI JWT>, state=<nonce>
activate Echo
Echo -> DB: Lookup LtiSession by nonce
DB --> Echo: LtiSession (with target_link_uri)
note right: Validate nonce is not expired
Echo -> DB: Find PlatformRegistration by iss\n(from id_token via DbToolConf)
DB --> Echo: PlatformRegistration
Echo -> Echo: pylti1p3.MessageLaunch.validate()
note right: Verifies JWT signature\nagainst Moodle's JWKS\nChecks aud, iss, exp, nonce
Echo -> Echo: Issue stateless session JWT
note right: Signed with Echo's RSA key\nContains sub, name, email,\nroles, course_id, course_title
Echo -> DB: Delete used LtiSession
Echo --> Frontend: Redirect with session_token=<JWT>
deactivate Echo

== Step 4: API Requests ==

Frontend -> Frontend: Store session_token
Frontend -> Echo: GET /api/endpoint\nAuthorization: Bearer <JWT>
activate Echo
Echo -> Echo: LTIAuthMiddleware validates JWT\n(injects request.state.lti_user)
Echo --> Frontend: Response
deactivate Echo

note over Echo: All subsequent requests\nvalidated via stateless JWT\nNo DB lookup needed

@enduml
```

## Source File

The raw PlantUML file is at `lti_launch_flow_diagram.puml`.

Render it at [plantuml.com](https://www.plantuml.com/plantuml/uml/) or with any PlantUML CLI tool.
