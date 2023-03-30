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
        td.appendChild(btn)
        tr.appendChild(td)

        tbody.appendChild(tr)
    }
    table.appendChild(tbody)
}

async function mettiNelCarrello(e) {
    console.log(e.target.id)
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

let modifica_attiva = false

function abilita_modifica() {
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
    
        for (let input of list) {
            let p = document.createElement("p")
            if(input.classList.contains("modified")) {
                let id = input.parentNode.parentNode.id
                let token = localStorage.getItem("token")
                let value = input.id
                console.log(value)
                if(value == "nome") net_update_event(token, id, nome=input.value)
                if(value == "prezzo") net_update_event(token, id, null, input.value)
                if(value == "quantita") net_update_event(token, id, null, null, input.value)
            }
            p.innerHTML = input.value
            p.id = input.id
            input.parentNode.replaceChild(p, input)
        }
    } 

    modifica_attiva = !modifica_attiva

}

async function invia_prodotto() {
    checkAdmin()
    let nome = document.getElementById("nome").value
    let costo = document.getElementById("costo").value
    let quantita = document.getElementById("quantita").value
    let token = localStorage.getItem("token")
    net_add_event(nome, parseInt(costo), parseInt(quantita), token)
}