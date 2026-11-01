// mapa.js — Localizacao da farmacia (partilhado por ajuda.html e portal.html)
//
// EDITA APENAS AQUI. Muda a morada e as coordenadas uma vez, e o mapa fica
// certo nas duas paginas.
//
// Como obter lat/lng: abre o Google Maps, carrega com o BOTAO DIREITO no local
// exato da farmacia -> aparece "14.xxxx, -23.xxxx". O 1o numero e a latitude,
// o 2o e a longitude.
const FARMACIA = {
    nome:   "Farmácia CV",
    morada: "Plateau, Praia — Ilha de Santiago, Cabo Verde",
    lat:    14.9177,
    lng:    -23.5092,
    zoom:   16
};

// Inicia o mapa Leaflet no div indicado. Preenche tambem (se existirem)
// o paragrafo da morada e o link de direcoes.
function iniciarMapaFarmacia(idMapa = "mapa", idMorada = "moradaFarmacia", idLink = "linkDirecoes") {
    const elMorada = document.getElementById(idMorada);
    if (elMorada) elMorada.textContent = FARMACIA.morada;

    const elLink = document.getElementById(idLink);
    if (elLink) elLink.href = `https://www.google.com/maps/dir/?api=1&destination=${FARMACIA.lat},${FARMACIA.lng}`;

    const mapa = L.map(idMapa).setView([FARMACIA.lat, FARMACIA.lng], FARMACIA.zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(mapa);
    L.marker([FARMACIA.lat, FARMACIA.lng]).addTo(mapa)
        .bindPopup(`<strong>${FARMACIA.nome}</strong><br>${FARMACIA.morada}`)
        .openPopup();

    return mapa;
}


// Mapa onde o utilizador MARCA um ponto (clicando). Chama `aoEscolher(lat, lng)`
// sempre que o ponto muda. Centra na farmacia por omissao.
function iniciarMapaSeletor(idMapa, aoEscolher, opcoes = {}) {
    const lat0 = opcoes.lat ?? FARMACIA.lat;
    const lng0 = opcoes.lng ?? FARMACIA.lng;
    const mapa = L.map(idMapa).setView([lat0, lng0], opcoes.zoom ?? 15);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(mapa);

    let marcador = null;
    function colocar(lat, lng, avisar = true) {
        if (marcador) {
            marcador.setLatLng([lat, lng]);
        } else {
            marcador = L.marker([lat, lng], { draggable: true }).addTo(mapa);
            marcador.on("dragend", () => {
                const p = marcador.getLatLng();
                if (aoEscolher) aoEscolher(p.lat, p.lng);
            });
        }
        if (avisar && aoEscolher) aoEscolher(lat, lng);
    }

    mapa.on("click", (e) => colocar(e.latlng.lat, e.latlng.lng, true));

    // Marcador inicial (ex.: ao editar um registo que ja tem coordenadas)
    if (opcoes.marcador && opcoes.marcador.lat != null && opcoes.marcador.lng != null) {
        colocar(opcoes.marcador.lat, opcoes.marcador.lng, false);
        mapa.setView([opcoes.marcador.lat, opcoes.marcador.lng], opcoes.zoom ?? 16);
    }

    return {
        mapa,
        colocar,
        limpar() { if (marcador) { mapa.removeLayer(marcador); marcador = null; } }
    };
}


// Mostra uma MORADA (texto) num mapa, dentro de um modal proprio (nao precisa
// de Bootstrap). Geocodifica via Nominatim (OpenStreetMap). Se nao localizar,
// mostra aviso + link para o Google Maps. Ideal para clientes/fornecedores
// que so tem morada escrita (sem coordenadas guardadas).
let _mapaMoradaObj = null;
function verMoradaNoMapa(endereco, titulo = "Localização", lat = null, lng = null) {
    endereco = (endereco || "").trim();
    const temCoords = (lat != null && lng != null && !isNaN(lat) && !isNaN(lng));

    let ov = document.getElementById("overlayMapaMorada");
    if (!ov) {
        ov = document.createElement("div");
        ov.id = "overlayMapaMorada";
        ov.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:3000;display:flex;align-items:center;justify-content:center;padding:16px;";
        ov.innerHTML =
            '<div style="background:#fff;border-radius:14px;max-width:640px;width:100%;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.3);">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #e5e7eb;">' +
                    '<strong id="mapaMoradaTitulo" style="font-size:15px;"></strong>' +
                    '<button id="mapaMoradaFechar" style="border:none;background:none;font-size:24px;line-height:1;cursor:pointer;color:#666;">&times;</button>' +
                '</div>' +
                '<div id="mapaMoradaInfo" style="padding:12px 18px 0;font-size:13.5px;color:#555;"></div>' +
                '<div id="mapaMoradaMapa" style="height:340px;margin:12px 18px 18px;border-radius:10px;"></div>' +
            '</div>';
        document.body.appendChild(ov);
        const fechar = () => { ov.style.display = "none"; };
        ov.querySelector("#mapaMoradaFechar").onclick = fechar;
        ov.onclick = (e) => { if (e.target === ov) fechar(); };
    }
    ov.style.display = "flex";
    document.getElementById("mapaMoradaTitulo").textContent = titulo;
    const info = document.getElementById("mapaMoradaInfo");
    info.innerHTML = endereco ? ("📍 " + endereco) : "<em>Sem morada registada.</em>";

    if (_mapaMoradaObj) { _mapaMoradaObj.remove(); _mapaMoradaObj = null; }
    _mapaMoradaObj = L.map("mapaMoradaMapa").setView([FARMACIA.lat, FARMACIA.lng], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(_mapaMoradaObj);
    setTimeout(() => { if (_mapaMoradaObj) _mapaMoradaObj.invalidateSize(); }, 60);

    // 1) Se ha coordenadas guardadas, usa-as diretamente (preciso, sem geocoding).
    if (temCoords) {
        _mapaMoradaObj.setView([+lat, +lng], 16);
        L.marker([+lat, +lng]).addTo(_mapaMoradaObj)
            .bindPopup("<strong>" + titulo + "</strong>" + (endereco ? "<br>" + endereco : "")).openPopup();
        info.innerHTML += ' <span style="color:#0e6b4f;">(ponto exato guardado)</span>';
        return;
    }

    // 2) Caso contrario, tenta localizar a morada em texto (Nominatim / OSM).
    if (!endereco) return;

    const consulta = encodeURIComponent(endereco + ", Cabo Verde");
    fetch("https://nominatim.openstreetmap.org/search?q=" + consulta + "&format=json&limit=1", {
        headers: { "Accept-Language": "pt" }
    })
    .then(r => r.json())
    .then(res => {
        if (res && res.length) {
            const lat = +res[0].lat, lon = +res[0].lon;
            _mapaMoradaObj.setView([lat, lon], 16);
            L.marker([lat, lon]).addTo(_mapaMoradaObj)
                .bindPopup("<strong>" + titulo + "</strong><br>" + endereco).openPopup();
        } else {
            info.innerHTML += ' <span style="color:#b45309;">— não foi possível localizar esta morada com precisão. ' +
                '<a href="https://www.google.com/maps/search/?api=1&query=' + consulta + '" target="_blank" rel="noopener">tentar no Google Maps ↗</a></span>';
        }
    })
    .catch(() => {
        info.innerHTML += ' <span style="color:#b45309;">— erro ao localizar. ' +
            '<a href="https://www.google.com/maps/search/?api=1&query=' + consulta + '" target="_blank" rel="noopener">abrir no Google Maps ↗</a></span>';
    });
}