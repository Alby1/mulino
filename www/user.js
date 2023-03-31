async function login() {
    let user = document.getElementById("user").value
    let pass = document.getElementById("pass").value

    let r = await net_login(user, pass)

    if(r["status"] == "ok"){
        localStorage.setItem("loggedIn", true)
        localStorage.setItem("username", user)
        localStorage.setItem("token", r["token"])
        localStorage.setItem("admin", r["admin"])
        window.location.replace("index.html")
    }
}

async function checkSession() {
    const t = localStorage.getItem("token")
    if(t == null) return false
    return await net_check_session(t)
}

function logout() {
    localStorage.removeItem("loggedIn")
    localStorage.removeItem("username")
    localStorage.removeItem("token")
    localStorage.removeItem("admin")
    localStorage.removeItem("cart")
}

function checkAdmin() {
    if(!checkSession()) return False
    let admin = localStorage.getItem("admin") == "true"
    return admin
}

async function register() {
    let user = document.getElementById("user").value
    let pass = document.getElementById("pass").value
    let passconf = document.getElementById("passconf").value
    let alert = document.getElementById("alert")
    alert.innerHTML = "Processing..."
    let alert_good = document.getElementById("alert-good")
    alert_good.innerHTML = ""
    

    if(pass != passconf) {
        alert.innerHTML = "Le password non sono uguali"
        return
    }

    r = await net_register(user, pass)
    if(r['status'] == "ok") {
        alert_good.innerHTML = "Registrazione avvenuta con successo!"
        alert.outerHTML = "<p id='alert'>(Ridirezionamento automatico...)</p>"
    } else if(r['status'] == "bad") {
        alert.innerHTML = "Registrazione fallita! Riprova."
    }
    await sleep(3000)
    window.location.replace("login.html")
}