async function products() {
    let prodotti = await request_products()

    const data_titles = ["nome", "prezzo", "quantita"]

    let table = document.getElementById("table")
    
/*     let thead = document.createElement("thead")
    
    let tr = document.createElement("tr")
    
    
    for (let t of data_titles){
        let th = document.createElement("th")
        th.innerHTML = capitalizeFirstLetter(t)
        tr.appendChild(th)
    }
    let th = document.createElement("th")
    th.innerHTML = "Aggiungi al carrello"
    tr.appendChild(th)
    
    thead.appendChild(tr)
    
    table.appendChild(thead) */

    let tbody = document.createElement("tbody")

    for(let prod of prodotti) {
        
        let tr = document.createElement("tr")

        tr.id = prod["id"]
        
        
        for (let t of data_titles){
            let td = document.createElement("td")
            let p = document.createElement("p")
            p.innerHTML = prod[t]
            p.id = t
            td.appendChild(p)
            tr.appendChild(td)
        }
        let td = document.createElement("td")
        let btn = document.createElement("button")
        btn.innerHTML = "Carrello"
        btn.id = prod["id"]
        btn.addEventListener("click", mettiNelCarrello)
        td.classList.add("active-session-action")
        td.appendChild(btn)
        tr.appendChild(td)
        
        td = document.createElement("td")
        let del = document.createElement("btn")
        del.innerHTML = "Elimina"
        del.id = prod["id"]
        del.addEventListener("click", elimina)
        td.classList.add("delete-button")
        td.hidden = true
        td.appendChild(del)
        tr.appendChild(td)


        tbody.appendChild(tr)
    }
    table.appendChild(tbody)
}

async function mettiNelCarrello(e) {
    let done = false
    let cart = JSON.parse(localStorage.getItem("cart"))
    if(cart == null) cart = []
    for (const item of cart) {
        if(item.id == e.target.id){
            let max = await net_check_product_availability(item.id)
            if(item.count < max) item.count += 1
            done = true
        }
    }
    if(!done) {
        cart.push({"id" : e.target.id, "count" : 1, "nome" : e.target.parentNode.parentNode.firstChild.firstChild.innerHTML, "token" : localStorage.getItem("token")})
    }
    localStorage.setItem("cart", JSON.stringify(cart))
}

async function elimina(e) {
    await net_delete_product(e.target.id, localStorage.getItem("token"))
    window.location.reload()
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

let modifica_attiva = false

async function abilita_modifica() {
    let del_list = document.getElementsByClassName("delete-button")
    for (let del of del_list) {
        del.hidden = modifica_attiva
    }
    if(!modifica_attiva) {
        let list = document.querySelectorAll("p")
        document.getElementById("abilita_modifica_button").innerHTML = "Applica modifiche"
        
        for (let p of list) {
            let input = document.createElement("input")
            input.value = p.innerHTML
            input.addEventListener("input", function(e) {
                e.target.classList.add("modified")
            })
            if(p.id == "quantita" || p.id == "prezzo") input.type = "number"
            input.id = p.id
            p.parentNode.replaceChild(input, p)
        }
        
    } else {
        document.getElementById("abilita_modifica_button").innerHTML = "Abilita modifica"
        let list = document.querySelectorAll("input")
        let any_changed = false
        
        for (let input of list) {
            let p = document.createElement("p")
            if(input.classList.contains("modified")) {
                any_changed=true

                let id = input.parentNode.parentNode.id
                let token = localStorage.getItem("token")
                let value = input.id

                if(value == "nome") await net_update_product(token, id, nome=input.value)
                if(value == "prezzo") await net_update_product(token, id, null, input.value)
                if(value == "quantita") await net_update_product(token, id, null, null, input.value)
            }
            p.innerHTML = input.value
            p.id = input.id
            input.parentNode.replaceChild(p, input)
        }
        if(any_changed) window.location.reload()
    } 

    modifica_attiva = !modifica_attiva

}

async function invia_prodotto() {
    checkAdmin()
    let nome = document.getElementById("nome").value
    let costo = document.getElementById("costo").value
    let quantita = document.getElementById("quantita").value
    let token = localStorage.getItem("token")
    net_add_product(nome, parseInt(costo), parseInt(quantita), token)
}