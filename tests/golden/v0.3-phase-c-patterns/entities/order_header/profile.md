---
type: entity
name: order_header
display: 주문
domain: [주문관리]
table: TB_ORDER_HEADER
status: draft
pattern: D2
columns:
  - { name: id,        type: bigserial,     pk: true, nullable: false }
  - { name: order_no,  type: varchar(50),   nullable: false }
  - { name: total_amt, type: numeric(12,2), nullable: true }
relations: []
sources: []
---

# order_header
