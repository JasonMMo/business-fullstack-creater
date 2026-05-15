 
# 제목 : business-fullstack-creater 플러그인 
## 목표 : 업무별 fullstack 코드 생성

## 목적 : 개발자가 프로젝트를 시작할 때 업무별로 premade 된 프로젝트 환경을 제공한다.

## 시나리오
"고객관리 업무 개발환경 만들어줘." 라고 하면 아래의 아키텍처를 가지는 프로젝트를 war 형태로 제공한다. 
## Architecture

- 3tier 구조를 기반으로 한다.
	- Front : nexacroN
	- Middle : Java Web Application - Spring boot
	- Backend : postgreSql
## Tech Spec

- NexacroN
- Jdk 17
- Spring booot 3.5
- xapi
- xeni
- uiadapter

## 주요 단계 : 업무별 DB 스키마(DDL) 생성 -> Java 서비스 생성 -> db 정보로 nexacro 화면 생성 -> war 다운로드

```
1. 	고객관리 프로세스 정의하기
		고객관리 업무를 단위도메인으로 구분하기
		단위도메인 별 관계 및 프로세스 정의하기
			단위도메인 세부업무 정의하기
				업무별 메뉴 정의하기
2. 	DB 스키마(DDL) 생성하기
		고객관리 관련 DB schema 정의
			단위도메인 세부업무 정의하기
				업무별 메뉴의 상세 sql 생성
					entity별 정합성 테스트
3. 	Java Web Application 구축
	 	nexacro 기반 어플리케이션 구조 생성
			단위도메인 세부업무 처리 정의하기
					업무별 메뉴의 상세기능 endpoint 정의
					상세기능 구현하기
						mapper sql (CRUD) 생성
						service interface 생성
						service 구현
						controller 생성
						endpoint 호출 테스트
4.	nexacro Project 생성
			업무별 메뉴 정의하기
				메뉴 등록
					상세기능 endpoint 정의
				업무별 메뉴 화면 구현하기
					nexacro 화면 생성
						세부업무별 상세기능 정의
							endpoint 호출 테스트
			 	
```

### 주요 단계별 처리 Plugin

| 순서  |    구분    |          주요 작업          |         참조 Plugin          |                                        활용 Skill                                         |
| :-: | :------: | :---------------------: | :------------------------: | :-------------------------------------------------------------------------------------: |
|  1  |   Plan   |     고객관리 프로세스 정의하기      |            ToDo            |                                                                                         |
|  2  | Backend  |    DB 스키마(DDL) 생성하기     |            ToDo            |                                                                                         |
|  3  |  Middle  | Java Web Application 구축 | /nexacro-fullstack-starter |                               /nexacro-fullstack-starter                                |
|  4  | Frontend |   nexacro Project 생성    | /nexacro-fullstack-starter | /nexacro-data-format<br>/nexacro-form-maker<br>/nexacro-project-maker<br>/nexacro-build |

## Plugin 구현 :: ToDo

### 1단계 : [[1. Plan - andrej-karpathy-rdb-skill 구현]]

- andrej-karpathy wiki를 관계형 DB에 맞도록 수정하여 구현
	- plugin 참조 URL : 
		- https://github.com/Benboerba620/karpathy-claude-wiki/tree/main#english
		- https://github.com/Benboerba620/karpathy-claude-wiki/blob/main/INSTALL-FOR-AI.md#33-update-template-frontmatter
- 위 참조 URL을 활용할 수 있는지 검토하고 활용할 수 없다면 새로 만든다.

### 2단계 : [[2. Backend - DB 스키마(DDL) 생성하기]]

- andrej-karpathy-skill을 적용
- 1단계 (Plan)에서 구현한 Plugin을 활용
	- 비즈니스의 각 도메인과 entity 요소를 리턴
	
## Plugin 활용

### 1단계 : Plan - 고객관리 프로세스 정의하기
- 1단계 (Plan)에서 구현한 Plugin.

### 2단계 : Backend - DB 스키마(DDL) 생성하기

- 1단계 (Plan)에서 구현한 Plugin을 활용
	- 비즈니스의 각 도메인과 entity 요소를 이용하여 DB 스키마(DDL) 생성하기
	
### 3~4단계 : Middle, Frontend - Java Web Application 및 nexacro Project 생성

```
/plugin marketplace add JasonMMo/nexacro-claude-skills

/plugin install nexacro-fullstack-starter@nexacro-claude-skills
/plugin install nexacro-claude-skills@nexacro-claude-skills
```

#### 활용 Skill

```
/nexacro-fullstack-starter
/nexacro-data-format
/nexacro-form-maker
/nexacro-project-maker
/nexacro-build
```


---

## 진행 상태 (2026-05-14 update — `nullable` 컬럼 키 정렬)

> Stage 1~3 모두 컬럼 `null:` 키가 YAML null 리터럴과 충돌하여 NOT NULL이 누락되던 버그 수정 — `nullable:` 키로 통일하고 레거시 `null:`/None 키는 로더에서 보정.

| 단계 | Plugin | 상태 |
| :-: | :-- | :-: |
| 1 | `andrej-karpathy-rdb-skill` | ✅ 완료 (v0.1.1) — `D:\AI\workspace\andrej-karpathy-rdb-skill` |
| 2 | `andrej-karpathy-rdb-ddl` | ✅ 완료 (v0.1.2) — `D:\AI\workspace\andrej-karpathy-rdb-ddl` |
| 3 | `andrej-karpathy-rdb-mybatis` | ✅ 완료 (v0.1.3) — `D:\AI\workspace\andrej-karpathy-rdb-mybatis` |
| 4 | `andrej-karpathy-rdb-nexacro` | ✅ 완료 (v0.1.0) — `D:\AI\workspace\andrej-karpathy-rdb-nexacro` |

### 참조 문서
- 설계: `docs/superpowers/specs/2026-05-13-andrej-karpathy-rdb-skill-design.md`
- 플랜: `docs/superpowers/plans/2026-05-13-andrej-karpathy-rdb-skill.md`
- 1단계: `needs/Plugin참조/1. Plan - andrej-karpathy-rdb-skill 구현.md`
- 2단계 입력 계약: `needs/Plugin참조/2. Backend - DB 스키마(DDL) 생성하기.md`
- 3~4단계 핸드오프 계약: `needs/Plugin참조/3. Middle+Frontend - Stage 3→4 nexacro 핸드오프 계약.md`
- 1단계 구현 레포: `D:\AI\workspace\andrej-karpathy-rdb-skill\`
- 2단계 구현 레포: `D:\AI\workspace\andrej-karpathy-rdb-ddl\`
- 3단계 구현 레포: `D:\AI\workspace\andrej-karpathy-rdb-mybatis\`
