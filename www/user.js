async function login() {
    let user = document.getElementById("user").value
    let pass = document.getElementById("pass").value

    let r = await net_login(user, pass)

    if(r["status"] == "ok"){
        localStorage.setItem("loggedIn", True)
        localStorage.setItem("username", user)
        localStorage.setItem("token", r["token"])
        window.location.replace("index.html")
    }
}