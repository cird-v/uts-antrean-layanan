// Membuat user admin dari environment (jenkins/.env) & melewati setup wizard.
// Dijalankan otomatis oleh Jenkins setiap start.
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.install.InstallState
import jenkins.model.Jenkins

def adminId = System.getenv('JENKINS_ADMIN_ID') ?: 'admin'
def adminPassword = System.getenv('JENKINS_ADMIN_PASSWORD')
def jenkins = Jenkins.get()

if (!adminPassword) {
    println '[init] JENKINS_ADMIN_PASSWORD kosong -> lewati pembuatan admin (pakai setup wizard)'
    return
}

def realm = jenkins.getSecurityRealm()
if (!(realm instanceof HudsonPrivateSecurityRealm)) {
    realm = new HudsonPrivateSecurityRealm(false)
    jenkins.setSecurityRealm(realm)
}
if (realm.getUser(adminId) == null) {
    realm.createAccount(adminId, adminPassword)
    println "[init] User admin '${adminId}' dibuat"
}

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
jenkins.setAuthorizationStrategy(strategy)
jenkins.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
jenkins.save()
