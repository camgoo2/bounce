# Event Invitation System Documentation

## System Flow

```mermaid
flowchart TD
    A[Event Created] --> B[Set Event Status: pending]
    B --> C[Add All Invitees with Priorities]
    C --> D[Find Highest Priority Invitee]
    D --> E[Set Event Status: active]
    E --> F[Wait for Response]
    
    F --> G{Response Type?}
    G -->|Accept| H[Event Complete ✅]
    G -->|Decline| I{More Invitees?}
    I -->|Yes| J[Invite Next Priority]
    I -->|No| K[Event Cancelled ❌]
    
    J --> F
    