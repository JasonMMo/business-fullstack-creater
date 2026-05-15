---
type: concept
kind: relation
name: role-has-many-user_role
cardinality: 1:N
from: app_role
to: app_user_role
fk_column: role_id
on_delete: cascade
status: draft
---

# app_role ↔ app_user_role
