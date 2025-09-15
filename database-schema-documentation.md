```mermaid
erDiagram
    User ||--o{ Event : creates
    User ||--o{ EventInvitee : "invited to"
    Event ||--o{ EventInvitee : "has invitees"
    
    User {
        int id
        string username
        string full_name
    }
    
    Event {
        int id
        string title
        int creator_id
        string status
        int current_invitee_id
        datetime created_at
    }
    
    EventInvitee {
        int id
        int event_id
        int invitee_id
        int priority
        string status
        datetime invited_at
    }