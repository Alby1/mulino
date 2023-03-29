async function login() {
    let user = document.getElementById("user").value
    let pass = document.getElementById("pass").value

    let r = await net_login(user, pass)

    if(r["status"] == "ok"){
        localStorage.setItem("loggedIn", true)
        localStorage.setItem("username", user)
        localStorage.setItem("token", r["token"])
        window.location.replace("index.html")
    }
}

async function checkSession() {
    const t = localStorage.getItem("token")
    return await net_check_session(t)
}

function logout() {
    localStorage.removeItem("loggedIn")
    localStorage.removeItem("username")
    localStorage.removeItem("token")
}