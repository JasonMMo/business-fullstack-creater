---
type: entity
name: product
display: 상품
domain: [상품관리]
table: TB_PRODUCT
status: draft
columns:
  - { name: id,    type: bigserial,    pk: true, nullable: false }
  - { name: name,  type: varchar(100), nullable: false }
  - { name: price, type: numeric(10,2), nullable: false }
relations: []
sources: []
---

# product
