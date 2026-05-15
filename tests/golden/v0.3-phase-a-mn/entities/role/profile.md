---
type: entity
name: app_role
display: 역할
domain: [인사관리]
table: role
status: draft
columns:
  - { name: id,   type: bigserial,   pk: true, nullable: false }
  - { name: code, type: varchar(50), nullable: false }
relations:
  - { kind: has_many, to: app_user_role, fk: role_id, concept: "[[role-has-many-user_role]]" }
sources: []
---

# app_role
