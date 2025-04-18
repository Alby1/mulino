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

    let tbody_ = document.getElementById("table-b")
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
        let td_ = document.createElement("td")
        let td = document.createElement("div")
        
        let btn = document.createElement("button")
        
        btn.id = prod["id"]
        btn.addEventListener("click", mettiNelCarrello)
        btn.style = "appearance: none;"
        img = document.createElement("img")
        img.src = "cart-plus.png"
        img.style = "width: 25px;"
        btn.appendChild(img)
        td_.classList.add("active-session-action")
        
        
        if(parseInt(prod["quantita"]) != 0) td.appendChild(btn)
        let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
        if(cart) {
            let cart_i = document.createElement("p")
            cart_i.innerHTML = "(0)"
            for (const obj of cart) {
                if(obj.id == prod["id"]) {
                    cart_i.innerHTML = `(${obj.count})`
                }
            }
            td.appendChild(cart_i)
        }
        td.classList.add("cart-add-index")
        
        
        td_.appendChild(td)
        tr.appendChild(td_)
        

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
    tbody.id = tbody_.id
    tbody_.replaceWith(tbody)
    table.appendChild(tbody)
}

async function mettiNelCarrello(e) {
    let done = false
    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    if(cart == null) cart = []
    let element
    if(e.target.tagName == "IMG") {element = e.target.parentNode}
    else {element = e.target}
    for (const item of cart) {
        if(item.id == element.id){
            let max = await net_check_product_availability(item.id)
            if(item.count < max) item.count += 1
            done = true
        }
    }
    if(!done) {
        cart.push({"id" : element.id, "count" : 1, "nome" : element.parentNode.parentNode.parentNode.firstChild.firstChild.innerHTML, "token" : localStorage.getItem(`${get_domain()}-token`)})
    }
    localStorage.setItem(`${get_domain()}-cart`, JSON.stringify(cart))
    products()
}

async function elimina(e) {
    await net_delete_product(e.target.id, localStorage.getItem(`${get_domain()}-token`))
    window.location.reload()
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

let modifica_attiva = false
let prev_quant = []

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
            if(p.id == "quantita") prev_quant.push({"value" : p.innerHTML, "id" : p.parentNode.parentNode.id})
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
                let token = localStorage.getItem(`${get_domain()}-token`)
                let type = input.id
                let value = input.value

                if(type == "nome") await net_update_product(token, id, value)
                if(type == "prezzo") await net_update_product(token, id, null, value)
                if(type == "quantita") {
                    let pq = null
                    for (const q of prev_quant) {
                        if(q.id == id) pq = q
                    }
                    await net_update_product(token, id, null, null, parseInt(pq.value) - value)
                }
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
    if(! await checkAdmin() ) return
    let nome = document.getElementById("nome").value
    let costo = document.getElementById("costo").value
    let quantita = document.getElementById("quantita").value
    let token = localStorage.getItem(`${get_domain()}-token`)
    net_add_product(nome, parseInt(costo), parseInt(quantita), token)
}