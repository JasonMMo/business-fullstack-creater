---
type: entity
name: code_master
display: 코드
domain: [주문관리]
table: TB_CODE_MASTER
status: draft
pattern: C1
columns:
  - { name: id,   type: bigserial,  pk: true, nullable: false }
  - { name: code, type: varchar(20), nullable: false }
  - { name: name, type: varchar(100), nullable: false }
relations: []
sources: []
---

# code_master
