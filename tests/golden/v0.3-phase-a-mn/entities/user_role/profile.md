---
type: entity
name: app_user_role
display: 사용자역할
domain: [인사관리]
table: user_role
status: draft
columns:
  - { name: user_id,    type: bigint,     pk: true, nullable: false }
  - { name: role_id,    type: bigint,     pk: true, nullable: false }
  - { name: created_at, type: timestamp,            nullable: true  }
sources: []
---

# app_user_role
