// app.js _ Utilitarios globais partilhados entre paginas

const API_URL = "http://127.0.0.1:8000";

function getToken() {
    return localStorage.getItem("token");
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + getToken()
    };
}
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function protegerPagina() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}
