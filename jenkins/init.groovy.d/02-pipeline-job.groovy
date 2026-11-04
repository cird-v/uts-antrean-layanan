// Membuat Pipeline job "queue-system-pipeline" (Pipeline script from SCM) jika belum ada:
//   - Repo GitHub + credential PAT `github-pat`, branch */main, Script Path: Jenkinsfile
//   - Trigger: GitHub hook trigger for GITScm polling (webhook)
import com.cloudbees.jenkins.GitHubPushTrigger
import com.coravy.hudson.plugins.github.GithubProjectProperty
import hudson.plugins.git.BranchSpec
import hudson.plugins.git.GitSCM
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty

def repoUrl = System.getenv('APP_REPO_URL')
def jobName = System.getenv('APP_JOB_NAME') ?: 'queue-system-pipeline'
def jenkins = Jenkins.get()

if (!repoUrl) {
    println '[init] APP_REPO_URL kosong -> lewati pembuatan job'
    return
}
if (jenkins.getItem(jobName) != null) {
    println "[init] Job '${jobName}' sudah ada"
    return
}

def scm = new GitSCM(GitSCM.createRepoList(repoUrl, 'github-pat'),
        [new BranchSpec('*/main')], null, null, [])
def definition = new CpsScmFlowDefinition(scm, 'Jenkinsfile')
definition.setLightweight(true)

def job = jenkins.createProject(WorkflowJob, jobName)
job.setDescription('CI/CD Student Service Queue System - dipicu GitHub Webhook (push ke main)')
job.setDefinition(definition)
job.addProperty(new GithubProjectProperty(repoUrl.replaceAll(/\.git$/, '/')))
job.addProperty(new PipelineTriggersJobProperty([new GitHubPushTrigger()]))
job.save()
println "[init] Job '${jobName}' dibuat untuk ${repoUrl}"
