from .db import get_connection

ESTADOS_VALIDOS = ("pendente", "confirmado", "pronto", "concluido", "cancelado")

# Transições que descontam ou repõem stock
ESTADOS_QUE_DESCONTAM_STOCK = {"confirmado"}
ESTADOS_QUE_REPOEM_STOCK = {"cancelado"}


def criar_pedido(cliente_id: int, itens: list, nota: str = None,
                 morada_entrega: str = None, entrega_lat: float = None, entrega_lng: float = None,
                 metodo_pagamento: str = None, cartao_ultimos4: str = None):
    """Cria um pedido a partir da lista de itens vinda do cliente. O preço
    é sempre recalculado a partir do medicamento na base de dados — nunca
    confiado ao valor enviado pelo browser. Não desconta stock ainda (só
    quando a farmácia confirmar o pedido)."""
    if not itens:
        raise ValueError("O pedido tem de ter pelo menos um item")

    conn = get_connection()

    cliente = conn.execute("SELECT id FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    if not cliente:
        conn.close()
        raise ValueError("Cliente não encontrado")

    itens_processados = []
    total = 0.0

    for item in itens:
        med = conn.execute(
            "SELECT * FROM medicamentos WHERE id = ?", (item["medicamento_id"],)
        ).fetchone()
        if not med:
            conn.close()
            raise ValueError(f"Medicamento #{item['medicamento_id']} não encontrado")

        if med["requer_receita"]:
            conn.close()
            raise ValueError(
                f"'{med['nome']}' exige receita médica e não pode ser encomendado online — "
                "dirija-se à farmácia com a receita"
            )

        quantidade = int(item["quantidade"])
        if quantidade <= 0:
            conn.close()
            raise ValueError("A quantidade tem de ser maior que zero")

        preco_unitario = med["preco"]
        subtotal = round(preco_unitario * quantidade, 2)
        total += subtotal

        itens_processados.append({
            "medicamento_id": med["id"],
            "medicamento_nome": med["nome"],
            "quantidade": quantidade,
            "preco_unitario": preco_unitario,
            "subtotal": subtotal
        })

    total = round(total, 2)

    # So marca como pago se veio um metodo de pagamento. Guarda apenas o metodo
    # e os ultimos 4 digitos — NUNCA o numero completo nem o CVV.
    pago = 1 if metodo_pagamento else 0
    cursor = conn.execute(
        """INSERT INTO pedidos
           (cliente_id, estado, total, nota, morada_entrega, entrega_lat, entrega_lng,
            metodo_pagamento, pago, cartao_ultimos4)
           VALUES (?, 'pendente', ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cliente_id, total, nota, morada_entrega, entrega_lat, entrega_lng,
         metodo_pagamento, pago, cartao_ultimos4)
    )
    pedido_id = cursor.lastrowid

    for item in itens_processados:
        conn.execute(
            """INSERT INTO pedido_itens
               (pedido_id, medicamento_id, medicamento_nome, quantidade, preco_unitario, subtotal)
               VALUES (?,?,?,?,?,?)""",
            (pedido_id, item["medicamento_id"], item["medicamento_nome"],
             item["quantidade"], item["preco_unitario"], item["subtotal"])
        )

    conn.commit()
    conn.close()
    return pedido_id


def _itens_do_pedido(conn, pedido_id):
    rows = conn.execute(
        "SELECT * FROM pedido_itens WHERE pedido_id = ?", (pedido_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def listar_pedidos():
    conn = get_connection()
    rows = conn.execute("""
        SELECT pedidos.*, clientes.nome AS cliente_nome, clientes.email AS cliente_email
        FROM pedidos
        JOIN clientes ON clientes.id = pedidos.cliente_id
        ORDER BY pedidos.id DESC
    """).fetchall()
    pedidos = []
    for r in rows:
        p = dict(r)
        p["itens"] = _itens_do_pedido(conn, p["id"])
        pedidos.append(p)
    conn.close()
    return pedidos


def listar_pedidos_por_cliente(cliente_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pedidos WHERE cliente_id = ? ORDER BY id DESC", (cliente_id,)
    ).fetchall()
    pedidos = []
    for r in rows:
        p = dict(r)
        p["itens"] = _itens_do_pedido(conn, p["id"])
        pedidos.append(p)
    conn.close()
    return pedidos


def obter_pedido(pedido_id: int):
    conn = get_connection()
    row = conn.execute("""
        SELECT pedidos.*, clientes.nome AS cliente_nome, clientes.email AS cliente_email
        FROM pedidos
        JOIN clientes ON clientes.id = pedidos.cliente_id
        WHERE pedidos.id = ?
    """, (pedido_id,)).fetchone()
    if not row:
        conn.close()
        return None
    pedido = dict(row)
    pedido["itens"] = _itens_do_pedido(conn, pedido_id)
    conn.close()
    return pedido


def atualizar_estado_pedido(pedido_id: int, novo_estado: str, usuario_email: str):
    if novo_estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado inválido: {novo_estado}")

    conn = get_connection()
    pedido = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if not pedido:
        conn.close()
        raise ValueError("Pedido não encontrado")

    estado_atual = pedido["estado"]
    if estado_atual == "concluido" or estado_atual == "cancelado":
        conn.close()
        raise ValueError(f"Não é possível alterar um pedido já '{estado_atual}'")

    itens = _itens_do_pedido(conn, pedido_id)

    # Confirmar o pedido -> descontar stock (validar que ha stock suficiente)
    if novo_estado in ESTADOS_QUE_DESCONTAM_STOCK and estado_atual not in ESTADOS_QUE_DESCONTAM_STOCK:
        for item in itens:
            med = conn.execute(
                "SELECT estoque FROM medicamentos WHERE id = ?", (item["medicamento_id"],)
            ).fetchone()
            if not med or med["estoque"] < item["quantidade"]:
                conn.close()
                raise ValueError(
                    f"Stock insuficiente para '{item['medicamento_nome']}' "
                    f"(pedido: {item['quantidade']}, disponível: {med['estoque'] if med else 0})"
                )
        for item in itens:
            conn.execute(
                "UPDATE medicamentos SET estoque = estoque - ? WHERE id = ?",
                (item["quantidade"], item["medicamento_id"])
            )

    # Cancelar um pedido que já tinha descontado stock -> repor
    if novo_estado in ESTADOS_QUE_REPOEM_STOCK and estado_atual in ESTADOS_QUE_DESCONTAM_STOCK:
        for item in itens:
            conn.execute(
                "UPDATE medicamentos SET estoque = estoque + ? WHERE id = ?",
                (item["quantidade"], item["medicamento_id"])
            )

    conn.execute(
        "UPDATE pedidos SET estado=?, atualizado_em=datetime('now'), atualizado_por=? WHERE id=?",
        (novo_estado, usuario_email, pedido_id)
    )
    conn.commit()
    conn.close()


def cancelar_pedido_cliente(pedido_id: int, cliente_id: int):
    """O próprio cliente só pode cancelar enquanto o pedido está 'pendente'
    (depois de confirmado, tem de contactar a farmácia)."""
    conn = get_connection()
    pedido = conn.execute(
        "SELECT * FROM pedidos WHERE id = ? AND cliente_id = ?", (pedido_id, cliente_id)
    ).fetchone()
    if not pedido:
        conn.close()
        raise ValueError("Pedido não encontrado")
    if pedido["estado"] != "pendente":
        conn.close()
        raise ValueError("Só é possível cancelar pedidos ainda pendentes — contacte a farmácia")

    conn.execute(
        "UPDATE pedidos SET estado='cancelado', atualizado_em=datetime('now') WHERE id=?",
        (pedido_id,)
    )
    conn.commit()
    conn.close()


def catalogo_disponivel():
    """Lista reduzida de medicamentos para o cliente ver no catálogo —
    sem expor a quantidade exata em stock, só se está disponível ou não.
    Medicamentos que exigem receita aparecem marcados e não podem ser
    adicionados ao carrinho (têm de ser comprados presencialmente)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nome, preco, categoria, estoque, requer_receita FROM medicamentos ORDER BY nome"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "nome": r["nome"],
            "preco": r["preco"],
            "categoria": r["categoria"],
            "requer_receita": bool(r["requer_receita"]),
            "disponivel": r["estoque"] > 0 and not r["requer_receita"]
        }
        for r in rows
    ]