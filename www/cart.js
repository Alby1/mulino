async function highercount(e) {
    let cart = JSON.parse(localStorage.getItem("cart"))
    let id = e.parentNode.id
    
    for (const c of cart) {
        if(c.id == id) {
            let max = await net_check_product_availability(c.id)
            if(c.count < max) c.count += 1
        }
    }
    localStorage.setItem("cart", JSON.stringify(cart))
    table()
}

function lowercount(e) {
    let cart = JSON.parse(localStorage.getItem("cart"))
    let id = e.parentNode.id
    for (const c of cart) {
        if(c.id == id && c.count > 1) {
            c.count -= 1
        }
    }
    localStorage.setItem("cart", JSON.stringify(cart))
    table()
}

function removeitem(e) {
    let cart = JSON.parse(localStorage.getItem("cart"))
    let id = e.parentNode.id
    for (const c of cart) {
        if(c.id == id) {
            c.count = 0
        }
    }
    localStorage.setItem("cart", JSON.stringify(cart))
    table()
}

async function table() {
    let table_ = document.getElementById("cart")
    let table = document.createElement("tbody")
    table.id = "cart"
    
    let cart = JSON.parse(localStorage.getItem("cart"))
    
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

    let bb = document.getElementById("buy-button")
    bb.disabled = table.children.length == 0
}

async function acquista() {
    let cart = JSON.parse(localStorage.getItem("cart"))
    let token = localStorage.getItem("token")

    console.log(await net_buy_products(cart, token))
}