function togglePwd() {
    const input = document.getElementById("password");
    const btn = document.getElementById("pwdToggleBtn");
    if (input.type === "password") {
        input.type = "text";
        btn.innerText = "🙈";
    } else {
        input.type = "password";
        btn.innerText = "👁";
    }
}

async function fazerLogin() {
    const email    = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value.trim();
    const erroBox  = document.getElementById("erro");
    const btn      = document.getElementById("btnLogin");

    erroBox.style.display = "none";

    if (!email || !password) {
        erroBox.innerText = "Preencha o e-mail e a senha.";
        erroBox.style.display = "block";
        return;
    }

    btn.disabled = true;
    btn.innerText = "A entrar...";

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (!res.ok) {
            erroBox.innerText = data.detail || "Credenciais inválidas.";
            erroBox.style.display = "block";
            return;
        }

        localStorage.setItem("token", data.access_token);
        localStorage.setItem("perfil", data.perfil);
        localStorage.setItem("nome", data.nome);
        window.location.href = data.perfil === "cliente" ? "portal.html" : "dashboard.html";

    } catch (err) {
        erroBox.innerText = "Erro de ligação com o servidor. Verifique se o backend está a correr.";
        erroBox.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.innerText = "Entrar";
    }
}

document.addEventListener("keydown", e => {
    if (e.key === "Enter") fazerLogin();
});