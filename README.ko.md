# tao-of-agent

[English](README.md)

[Vercel agent skills](https://vercel.com/docs/agent-resources/skills) 형식을 따르는 에이전트
스킬 모음입니다. 스킬 하나는 `skills/` 아래의 디렉터리 하나이고, 그 안에 `SKILL.md`가 있습니다.

## 스킬

| 스킬 | 설명 |
| --- | --- |
| [`minimal-code`](skills/minimal-code) | 정확하고 읽기 쉬우며 테스트된 변경을 가장 작게 만듭니다. KISS, YAGNI, DRY, 명시적인 오류 처리, TDD를 따릅니다. |
| [`git-hygiene`](skills/git-hygiene) | 개발 중에는 리뷰하기 쉽고 병합 후에는 의미가 남는 Git 이력을 유지합니다. |
| [`natural-clear-writing`](skills/natural-clear-writing) | 상투적인 AI 문체 없이 글을 쓰거나 고칩니다. 한국어에는 추가 규칙을 적용합니다. |

## 설치

### Claude Code 플러그인으로 설치

이 저장소는 플러그인 마켓플레이스이며, 위의 모든 스킬을 담은 플러그인 `tao` 하나를 제공합니다.
Claude Code 안에서 다음을 실행합니다.

```text
/plugin marketplace add recursivecurry/tao-of-agent
/plugin install tao@tao-of-agent
```

플러그인의 스킬에는 네임스페이스가 붙습니다: `tao:minimal-code`, `tao:git-hygiene`,
`tao:natural-clear-writing`.

### Codex 플러그인으로 설치

이 저장소는 Codex 마켓플레이스이기도 하며, Codex에 맞춰 만든 별도의 `tao` 플러그인을 제공합니다.

```bash
codex plugin marketplace add recursivecurry/tao-of-agent
codex plugin add tao@tao-of-agent
```

플러그인에는 hook이 들어 있고, Codex는 사용자가 승인한 뒤에만 플러그인의 hook을 실행합니다.
승인 화면은 다음 세션을 시작할 때 나타납니다. 스킬은 승인하지 않아도 동작하지만 hook은
동작하지 않습니다.

나중에 업데이트하려면 다음을 실행합니다.

```bash
codex plugin marketplace upgrade tao-of-agent
codex plugin add tao@tao-of-agent
```

### skills CLI로 설치

[skills CLI](https://vercel.com/docs/agent-resources/skills)는 지원하는 모든 에이전트에 스킬을
설치합니다. 위에 플러그인이 없는 에이전트에 사용하세요. 한 에이전트에 플러그인과 이 스킬을
함께 설치하면 모든 스킬이 `tao:minimal-code`와 `minimal-code`로 두 번 로드되므로 둘 중 하나만
고르세요. 저장소의 모든 스킬을 설치하려면 다음을 실행합니다.

```bash
npx skills add recursivecurry/tao-of-agent
```

하나만 골라 설치할 수도 있습니다.

```bash
npx skills add recursivecurry/tao-of-agent --skill minimal-code
npx skills add recursivecurry/tao-of-agent --skill git-hygiene
npx skills add recursivecurry/tao-of-agent --skill natural-clear-writing
```

전역으로 설치하려면 `-g`를, 특정 에이전트를 지정하려면 `-a claude-code`를 붙입니다. 이렇게
설치한 스킬은 접두사 없는 이름(`minimal-code`, `git-hygiene`, `natural-clear-writing`)을
그대로 씁니다.

### 수동 설치

Claude Code에서는 스킬 디렉터리를 복사합니다. `references/` 하위 디렉터리가 있으면 함께
복사합니다.

```bash
cp -r skills/minimal-code ~/.claude/skills/
cp -r skills/natural-clear-writing ~/.claude/skills/
```

## 플러그인이 추가하는 것

두 플러그인은 세션을 시작할 때마다 hook을 실행해 짧은 지침 두 가지를 넣습니다. 하나는 코드를
바꿀 때 `tao:minimal-code`를 따르고 완료를 보고하기 전에 그 스킬의 완료 체크리스트를 점검하라는
지침이고, 다른 하나는 일반 답변에서 상투적인 표현을 쓰지 말라는 지침입니다. 아래 두 절은 그
이유를 설명하고, 플러그인 없이 스킬만 설치한 경우 직접 붙여 넣을 같은 문구를 제공합니다.

## `minimal-code`를 항상 적용하기

에이전트는 스킬이 관련 있다고 판단할 때만 스킬을 로드하고, 그것도 작업을 *시작*할 때
로드합니다. 완료 전 체크리스트가 가장 필요한 작업의 끝에서는 로드하지 않습니다. 코딩 원칙은
모든 변경에 적용되어야 합니다. 플러그인은 hook으로 이 문제를 해결합니다. 플러그인이 없다면
프로젝트의 `CLAUDE.md`(또는 `AGENTS.md`)에 스킬을 가리키는 문구를 넣어 보완하세요.

```markdown
Follow the minimal-code skill when writing or changing code.

Load it before making code changes. Before reporting a change as done, read
references/done-checklist.md from the skill directory and work through it.
```

세부 내용은 스킬에 있습니다. 이 문구는 변경이 작게 유지될지를 좌우하는 두 시점에 에이전트가
스킬을 참조하게 합니다. 완료 체크리스트를 별도 파일로 둔 것은 두 번째 시점에 스킬 전체를 다시
로드하지 않고 짧은 파일 하나만 읽게 하기 위해서입니다.

## `natural-clear-writing`을 일반 답변에도 적용하기

이 스킬은 글을 쓰거나 고치는 작업에서만 로드되고 일반 답변에서는 로드되지 않습니다.
플러그인은 요약한 규칙을 모든 세션에 넣습니다. 플러그인이 없다면 `CLAUDE.md`(또는
`AGENTS.md`)에 다음을 넣으세요.

```markdown
Lead replies with the answer. No staged openers, empty contrasts, forced triads,
dramatic closers, or Markdown decoration. Load natural-clear-writing when
writing or editing prose, docs, commit messages, or UI strings.
```

## 평가

`evals/`에는 `natural-clear-writing`의 평가 케이스가 있습니다. 영어 문서, 한국어 문서, 두
언어가 섞인 메모, 플레이스홀더가 있는 UI 문자열, 커밋 메시지입니다. 각 케이스에는 LLM 채점기가
있어 상투적인 표현이 사라졌는지, 모든 사실과 플레이스홀더와 어조가 보존되었는지 확인합니다.

```bash
tools/eval.sh --judge-model sonnet
```

기본 채점 모델(haiku)은 한국어 채점 기준을 잘못 읽으므로 더 강한 모델을 지정하세요. 실행하면
플러그인이 없는 기준선도 함께 채점해 차이를 보고합니다. 스킬을 수정할 때 살펴볼 숫자가 이
차이입니다. 결과는 `evals/results/`에 저장되며, 이 디렉터리는 git이 무시합니다.

`claude plugin eval`은 플러그인 디렉터리 안의 케이스만 읽는데, 평가 케이스는 플러그인에
포함되어 배포되지 않습니다. 그래서 이 스크립트는 출력을 다시 빌드하고 `plugins/claude/tao/`와
`evals/`를 임시 디렉터리에 복사한 뒤 거기서 평가를 실행합니다. 추가 인자는 그대로 전달됩니다.
저장소 루트에서 `claude plugin eval .`을 실행하지 마세요. 케이스는 찾지만 플러그인을 로드하지
않습니다.

## 저장소 구조

```text
src/skills/<skill>/SKILL.md.tmpl   스킬 소스: 여기를 수정합니다
src/plugin/                        두 플러그인에 모두 들어가는 파일
src/claude/                        Claude Code 매니페스트와 Claude 전용 파일
src/codex/                         Codex 매니페스트와 Codex 전용 파일
tools/build.py                     아래의 모든 것을 생성합니다
skills/                            생성됨, skills CLI가 읽습니다
plugins/claude/tao/                생성됨, Claude Code 플러그인
plugins/codex/tao/                 생성됨, Codex 플러그인
.claude-plugin/marketplace.json    생성됨, Claude Code 마켓플레이스
.agents/plugins/marketplace.json   생성됨, Codex 마켓플레이스
evals/                             평가 케이스, 배포되지 않습니다
```

`skills/`, `plugins/`, `.claude-plugin/`, `.agents/plugins/`는 빌드 출력입니다. 모든 설치
도구가 기본 브랜치를 읽기 때문에 이 디렉터리들을 커밋해 둡니다. 빌드는 이 디렉터리에서 자신이
만들지 않은 파일을 삭제하므로, 직접 수정한 내용이나 추가한 파일은 남지 않습니다.

## 기여하기

세 배포판 모두에서 동작하는 스킬을 쓰기 위한 규칙은 [AGENTS.md](AGENTS.md)에 있습니다. Claude
Code와 Codex는 이 저장소에서 작업할 때 이 파일을 읽습니다.

1. `src/` 아래의 파일을 수정합니다. `.tmpl` 파일은 배포판마다 한 번씩 렌더링되고, 나머지
   파일은 그대로 복사됩니다. 템플릿이 target block을 쓰지 않는 한 모든 배포판에 같은 글이
   들어갑니다.

   ```markdown
   <!-- target:claude -->
   이 줄은 Claude Code 플러그인에만 들어갑니다.
   <!-- /target -->
   ```

   타깃은 `claude`, `codex`, `generic`입니다. 마커는 한 줄 전체를 차지해야 하고, 블록은
   중첩할 수 없습니다.

   한 에이전트만 지원하는 것은 그 에이전트의 디렉터리에 둡니다. hook 정의, subagent, 그
   에이전트의 변수 이름을 쓰는 파일이 여기에 해당합니다. `src/claude/`는 Claude Code
   플러그인으로, `src/codex/`는 Codex 플러그인으로 복사됩니다. lint는 이 디렉터리에 다른
   에이전트의 변수와 경로가 있으면 거부합니다. 예를 들어 `src/claude/`의 `${PLUGIN_ROOT}`나
   `src/codex/`의 `${CLAUDE_PLUGIN_ROOT}`입니다. 두 플러그인에 모두 필요한 파일은
   `src/plugin/`에 둡니다.
2. 변경이 플러그인에 영향을 주면 `src/claude/plugin.json`과 `src/codex/plugin.json`의
   `version`을 함께 올립니다. 두 값은 같아야 합니다. 설치된 플러그인은 버전이 바뀔 때만
   업데이트되고, 버전을 올리지 않으면 빌드 PR의 버전 검사가 실패합니다.
3. 검사를 실행합니다.

   ```bash
   python3 -m unittest discover -s tools
   python3 tools/build.py lint
   tools/check_codex_plugin.sh   # codex CLI가 필요하고, 로그인은 필요 없습니다
   ```

4. `src/` 변경으로 pull request를 엽니다. 생성된 파일은 커밋하지 않아도 됩니다. 커밋한다면
   먼저 `python3 tools/build.py build`를 실행해 `python3 tools/build.py check`가 통과하게
   하세요.

pull request가 병합되면 워크플로가 다시 빌드한 출력으로 "Release: regenerate distributions"
pull request를 엽니다. 이 pull request를 병합하는 것이 릴리스입니다. 여기에 필요한 1회성 설정은
[docs/release-setup.md](docs/release-setup.md)에 있습니다.
