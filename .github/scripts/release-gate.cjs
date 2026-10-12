// Only trusted branch pushes can supply code to privileged release workflows.
module.exports = async ({github, context, core}) => {
  const run = context.payload.workflow_run;
  const branch = run ? run.head_branch : context.ref.replace('refs/heads/', '');
  const sha = run ? run.head_sha : context.sha;
  if (!['dev', 'main'].includes(branch) ||
      (run && (run.event !== 'push' || run.head_repository.full_name !== `${context.repo.owner}/${context.repo.repo}`))) {
    throw new Error('Releases require a trusted dev/main branch push or dispatch.');
  }
  const {data: head} = await github.rest.repos.getBranch({...context.repo, branch});
  if (head.commit.sha !== sha) {
    core.notice('Skipping superseded commit; only the current branch head is published.');
    return false;
  }
  for (const workflow_id of ['ci.yml', 'hassfest.yml', 'gitleaks.yml']) {
    const runs = await github.paginate(github.rest.actions.listWorkflowRuns, {
      ...context.repo, workflow_id, branch, event: 'push', head_sha: sha, per_page: 100,
    });
    const latest = runs.filter(item => item.head_sha === sha)
      .sort((a, b) => b.id - a.id || b.run_attempt - a.run_attempt)[0];
    if (!latest || latest.status !== 'completed' || latest.conclusion !== 'success') {
      const message = `${workflow_id} has not passed for ${sha}; publication is blocked.`;
      if (context.eventName === 'workflow_dispatch') throw new Error(message);
      core.notice(message);
      return false;
    }
  }
  return true;
};
