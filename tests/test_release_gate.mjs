import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const gate = createRequire(import.meta.url)("../.github/scripts/release-gate.cjs");
const sha = "a".repeat(40);

function fixture({ dispatch = false, branch = "dev", head = sha, runs = {} } = {}) {
  const context = {
    repo: { owner: "example", repo: "integration" },
    ref: `refs/heads/${branch}`, sha,
    eventName: dispatch ? "workflow_dispatch" : "workflow_run",
    payload: dispatch ? {} : { workflow_run: {
      head_branch: branch, head_sha: sha, event: "push",
      head_repository: { full_name: "example/integration" },
    } },
  };
  const calls = [];
  const notices = [];
  return {
    context, calls, notices,
    core: { notice: message => notices.push(message) },
    github: {
      rest: {
        repos: { getBranch: async () => ({ data: { commit: { sha: head } } }) },
        actions: { listWorkflowRuns: Symbol("listWorkflowRuns") },
      },
      paginate: async (_method, args) => {
        calls.push(args);
        return runs[args.workflow_id] ?? [{ id: 1, head_sha: sha, status: "completed", conclusion: "success" }];
      },
    },
  };
}

test("gates all validation workflows on exact trusted push SHA", async () => {
  for (const branch of ["dev", "main"]) {
    const state = fixture({ branch });
    assert.equal(await gate(state), true);
    assert.deepEqual(state.calls.map(call => call.workflow_id), ["ci.yml", "hassfest.yml", "gitleaks.yml"]);
    assert.ok(state.calls.every(call => call.branch === branch && call.head_sha === sha && call.event === "push"));
  }
});

test("rejects forks, PR events and unrelated branches before querying", async () => {
  for (const change of [
    state => { state.context.payload.workflow_run.event = "pull_request"; },
    state => { state.context.payload.workflow_run.head_repository.full_name = "fork/integration"; },
    state => { state.context.payload.workflow_run.head_branch = "feature/example"; },
  ]) {
    const state = fixture();
    change(state);
    await assert.rejects(gate(state), /trusted/);
    assert.equal(state.calls.length, 0);
  }
});

test("skips superseded branch commits", async () => {
  const state = fixture({ head: "b".repeat(40) });
  assert.equal(await gate(state), false);
  assert.equal(state.calls.length, 0);
  assert.match(state.notices[0], /superseded/);
});

test("pending, failed, missing or wrong-SHA checks block publication", async () => {
  for (const checks of [
    [],
    [{ id: 1, head_sha: sha, status: "in_progress", conclusion: null }],
    [{ id: 1, head_sha: sha, status: "completed", conclusion: "failure" }],
    [{ id: 1, head_sha: "b".repeat(40), status: "completed", conclusion: "success" }],
  ]) {
    const state = fixture({ runs: { "hassfest.yml": checks } });
    assert.equal(await gate(state), false);
    assert.match(state.notices[0], /hassfest.yml.*blocked/);
  }
});

test("latest failing run takes precedence over older success", async () => {
  const state = fixture({ runs: { "gitleaks.yml": [
    { id: 2, head_sha: sha, status: "completed", conclusion: "failure" },
    { id: 1, head_sha: sha, status: "completed", conclusion: "success" },
  ] } });
  assert.equal(await gate(state), false);
});

test("dispatch requires branch and all successful push gates", async () => {
  assert.equal(await gate(fixture({ dispatch: true, branch: "main" })), true);
  await assert.rejects(gate(fixture({ dispatch: true, branch: "feature" })), /trusted/);
  await assert.rejects(gate(fixture({ dispatch: true, runs: { "ci.yml": [] } })), /ci.yml.*blocked/);
});

test("API errors are not converted into success", async () => {
  const state = fixture();
  state.github.paginate = async () => { throw new Error("permission denied"); };
  await assert.rejects(gate(state), /permission denied/);
});
