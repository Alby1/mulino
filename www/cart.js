async function highercount(e) {
    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    let id = e.parentNode.id
    
    for (const c of cart) {
        if(c.id == id) {
            let max = await net_check_product_availability(c.id)
            if(c.count < max) c.count += 1
        }
    }
    localStorage.setItem(`${get_domain()}-cart`, JSON.stringify(cart))
    table()
}

function lowercount(e) {
    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    let id = e.parentNode.id
    for (const c of cart) {
        if(c.id == id && c.count > 1) {
            c.count -= 1
        }
    }
    localStorage.setItem(`${get_domain()}-cart`, JSON.stringify(cart))
    table()
}

function removeitem(e) {
    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    let id = e.parentNode.id
    for (const c of cart) {
        if(c.id == id) {
            c.count = 0
        }
    }
    localStorage.setItem(`${get_domain()}-cart`, JSON.stringify(cart))
    table()
}

async function table() {
    let table_ = document.getElementById("cart")
    let table = document.createElement("tbody")
    table.id = "cart"
    
    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    if(cart) {
        for (const obj of cart) {
            if(obj.count > 0) {
                let tr = document.createElement("tr")
                tr.id = obj.id
                
                let td = document.createElement("td")
                td.innerHTML = obj.nome
                tr.appendChild(td)
    
                td = document.createElement("td")
                td.innerHTML = obj.count
                tr.appendChild(td)
    
                td = document.createElement("td")
                td.innerHTML = document.getElementById("action-prefab").innerHTML
                td.id = obj.id
    
                tr.appendChild(td)
                
                table.appendChild(tr)
            }
        }
        table_.replaceWith(table)
    }
    

    let bb = document.getElementById("buy-button")
    let sb = document.getElementById("svuota-button")
    let adr = document.getElementById("address")
    bb.disabled = table.children.length == 0
    sb.disabled = table.children.length == 0
    adr.disabled = table.children.length == 0
}

async function acquista() {
    let bb = document.getElementById("buy-button")
    bb.disabled = true
    let alert = document.getElementById("alert")
    let alert_good = document.getElementById("alert-good")
    alert.innerHTML = ""
    alert_good.innerHTML = ""

    let cart = JSON.parse(localStorage.getItem(`${get_domain()}-cart`))
    let adr = document.getElementById("address")
    if(adr.value.length == 0){
        alert.innerHTML = "L'indirizzo non può essere vuoto"
        bb.disabled = false
        return
    }

    cart[0].address = adr.value
    let token = localStorage.getItem(`${get_domain()}-token`)
    
    let buy = await net_buy_products(cart, token)
    if(buy) {
        alert.innerHTML = buy
        return
    }
    localStorage.removeItem(`${get_domain()}-cart`)
    alert_good.innerHTML = "Acquisto avvenuto con successo (attendere...)"
    await sleep(5000)
    window.location.reload()
}

function svuota() {
    localStorage.removeItem(`${get_domain()}-cart`)
    window.location.reload()
}