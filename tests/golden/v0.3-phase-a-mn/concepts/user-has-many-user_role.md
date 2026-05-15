---
type: concept
kind: relation
name: user-has-many-user_role
cardinality: 1:N
from: app_user
to: app_user_role
fk_column: user_id
on_delete: cascade
status: draft
---

# app_user ↔ app_user_role
