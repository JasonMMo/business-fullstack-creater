---
type: entity
name: order_detail
display: 주문상세
domain: [주문관리]
table: TB_ORDER_DETAIL
status: draft
pattern: F1
columns:
  - { name: id,        type: bigserial,     pk: true, nullable: false }
  - { name: header_id, type: bigint,        nullable: false }
  - { name: line_no,   type: int,           nullable: false }
  - { name: qty,       type: numeric(10,2), nullable: true }
relations: []
sources: []
---

# order_detail
