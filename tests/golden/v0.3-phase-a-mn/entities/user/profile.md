---
type: entity
name: app_user
display: 사용자
domain: [인사관리]
table: user
status: draft
columns:
  - { name: id,   type: bigserial,    pk: true, nullable: false }
  - { name: name, type: varchar(100), nullable: false }
relations:
  - { kind: has_many, to: app_user_role, fk: user_id, concept: "[[user-has-many-user_role]]" }
sources: []
---

# app_user
