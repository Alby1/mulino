async function login() {
    let user = document.getElementById("user").value
    let pass = document.getElementById("pass").value

    try{
        let alert = document.getElementById("alert")
        let alert_good = document.getElementById("alert-good")

        alert.innerHTML = ""
        alert_good.innerHTML = "Processing..."
    } catch {}

    let r = await net_login(user, pass)

    if(r["status"] == "ok"){
        try{
            let alert_good = document.getElementById("alert-good")

            alert_good.innerHTML = "Login avvenuto con successo (attendere, ridirezionamento automatico...)"
        } catch {}
        let dm = get_domain()
        localStorage.setItem(`${dm}-loggedIn`, true)
        localStorage.setItem(`${dm}-username`, user)
        localStorage.setItem(`${dm}-token`, r["token"])
        localStorage.setItem(`${dm}-admin`, r["admin"])

        if(window.location.pathname.startsWith("/admin")) {
            window.location.replace("/admin")
            return
        }
        window.location.replace("index.html")
    } else {
        try{
            let alert = document.getElementById("alert")
            let alert_good = document.getElementById("alert-good")

            alert.innerHTML = r["message"]
            alert_good.innerHTML = ""
        } catch {}
    }
}

function get_domain() {
    return window.location.pathname.split("/")[1]
}

async function checkSession() {
    const t = localStorage.getItem(`${get_domain()}-token`)
    if(t == null) return false
    return await net_check_session(t)
}

function logout() {
    let dm = get_domain()
    localStorage.removeItem(`${dm}-loggedIn`)
    localStorage.removeItem(`${dm}-username`)
    localStorage.removeItem(`${dm}-token`)
    localStorage.removeItem(`${dm}-admin`)
    localStorage.removeItem(`${dm}-cart`)
}

async function checkAdmin() {
    if(! await checkSession()) return false
    let admin = localStorage.getItem(`${get_domain()}-admin`) == "true"
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