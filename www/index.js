async function products() {
    let pr = await request_products()

    const data_titles = ["nome", "prezzo", "quantita"]

    
    let table = document.getElementById("table")
    let thead = document.createElement("thead")
    
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
    
    table.appendChild(thead)

    let tbody = document.createElement("tbody")

    for(let a of pr) {
        
        let tr = document.createElement("tr")
    
        
        for (let t of data_titles){
            let td = document.createElement("td")
            td.innerHTML = a[t]
            tr.appendChild(td)
        }
        let td = document.createElement("td")
        let btn = document.createElement("button")
        btn.innerHTML = "Carrello"
        btn.id = a["id"]
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