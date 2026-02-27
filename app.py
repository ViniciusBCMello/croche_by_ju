from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os
import mercadopago

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///croche_store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN) if MERCADOPAGO_ACCESS_TOKEN else None

db = SQLAlchemy(app)


# ── MODELOS ───────────────────────────────────────────────────────────────────

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<AdminUser {self.username}>'


class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(200))
    prazo_dias = db.Column(db.Integer, default=7)
    categoria = db.Column(db.String(50))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    disponivel = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Produto {self.nome}>'


class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text, nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'))
    quantidade = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pendente')
    status_pagamento = db.Column(db.String(20), default='Pendente')
    payment_id = db.Column(db.String(100))
    preference_id = db.Column(db.String(100))
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)

    produto = db.relationship('Produto', backref='pedidos')


# ── SETUP DO BANCO ────────────────────────────────────────────────────────────

def init_db():
    """Cria as tabelas e o admin padrão se não existir nenhum usuário."""
    db.create_all()
    if AdminUser.query.count() == 0:
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin = AdminUser(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"[!] Admin padrão criado: usuario='{username}' — troque a senha pelo painel!")


if os.getenv("RENDER"):
    with app.app_context():
        init_db()


# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Faça login para acessar o painel.', 'warning')
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_produtos'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin = AdminUser.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session.permanent = True
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            flash(f'Bem-vinda, {admin.username}!', 'success')
            next_url = request.args.get('next') or url_for('admin_produtos')
            return redirect(next_url)
        else:
            flash('Usuário ou senha incorretos.', 'error')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Você saiu do painel com segurança.', 'success')
    return redirect(url_for('index'))


@app.route('/admin/alterar-senha', methods=['GET', 'POST'])
@login_required
def admin_alterar_senha():
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmar = request.form.get('confirmar_senha', '')
        admin = AdminUser.query.filter_by(username=session['admin_username']).first()

        if not admin.check_password(senha_atual):
            flash('Senha atual incorreta.', 'error')
        elif len(nova_senha) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'error')
        elif nova_senha != confirmar:
            flash('As senhas não coincidem.', 'error')
        else:
            admin.set_password(nova_senha)
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('admin_produtos'))

    return render_template('admin_alterar_senha.html')


# ── ROTAS PÚBLICAS ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    produtos_destaque = Produto.query.limit(6).all()
    return render_template('index.html', produtos=produtos_destaque)


@app.route('/carrinho')
def carrinho():
    return render_template('carrinho.html')


@app.route('/produtos')
def produtos():
    categoria = request.args.get('categoria')
    if categoria:
        lista_produtos = Produto.query.filter_by(categoria=categoria).all()
    else:
        lista_produtos = Produto.query.all()
    categorias = db.session.query(Produto.categoria).distinct().all()
    return render_template('produtos.html', produtos=lista_produtos, categorias=categorias)


@app.route('/produto/<int:id>')
def produto_detalhe(id):
    produto = Produto.query.get_or_404(id)
    return render_template('produto_detalhe.html', produto=produto)


@app.route('/finalizar-compra', methods=['GET', 'POST'])
def finalizar_compra():
    if request.method == 'POST':

        # ── 1. Validar produto_id ─────────────────────────────────────────────
        try:
            produto_id = int(request.form.get('produto_id', 0))
        except (ValueError, TypeError):
            flash('Requisição inválida.', 'error')
            return redirect(url_for('produtos'))

        # ── 2. Validar quantidade (1 a 99) ────────────────────────────────────
        try:
            quantidade = int(request.form.get('quantidade', 1))
            if quantidade < 1 or quantidade > 99:
                raise ValueError
        except (ValueError, TypeError):
            flash('Quantidade inválida. Permitido entre 1 e 99.', 'error')
            return redirect(url_for('produtos'))

        # ── 3. Validar campos obrigatórios ────────────────────────────────────
        nome     = request.form.get('nome', '').strip()
        email    = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        endereco = request.form.get('endereco', '').strip()

        if not all([nome, email, endereco]):
            flash('Preencha todos os campos obrigatórios.', 'error')
            return redirect(url_for('finalizar_compra'))

        # ── 4. Verificar produto no banco (nunca confiar no cliente) ──────────
        produto = Produto.query.get(produto_id)
        if not produto or not produto.disponivel:
            flash('Produto indisponível para encomenda no momento.', 'error')
            return redirect(url_for('produtos'))

        # ── 5. Calcular total server-side (ignorar qualquer valor do cliente) ─
        total = produto.preco * quantidade

        # ── 6. Criar pedido APENAS se o Mercado Pago responder OK ─────────────
        pedido = Pedido(
            nome_cliente=nome,
            email=email,
            telefone=telefone,
            endereco=endereco,
            produto_id=produto_id,
            quantidade=quantidade,
            total=total
        )
        db.session.add(pedido)
        db.session.commit()

        if sdk and MERCADOPAGO_ACCESS_TOKEN:
            try:
                preference_data = {
                    "items": [{"title": produto.nome, "quantity": quantidade,
                                "unit_price": float(produto.preco), "currency_id": "BRL"}],
                    "payer": {"name": nome, "email": email},
                    "back_urls": {
                        "success": url_for('pagamento_sucesso', pedido_id=pedido.id, _external=True),
                        "failure": url_for('pagamento_falha', pedido_id=pedido.id, _external=True),
                        "pending": url_for('pagamento_pendente', pedido_id=pedido.id, _external=True)
                    },
                    "external_reference": str(pedido.id)
                }
                preference_response = sdk.preference().create(preference_data)
                preference = preference_response.get("response", preference_response)
                pedido.preference_id = preference["id"]
                db.session.commit()
                init_point = preference.get("init_point") or preference.get("sandbox_init_point")
                return redirect(init_point)

            except Exception as e:
                import traceback; traceback.print_exc()
                # Mercado Pago falhou — remove o pedido para não poluir o banco
                db.session.delete(pedido)
                db.session.commit()
                flash('Erro ao processar pagamento. Tente novamente ou entre em contato.', 'error')
                return redirect(url_for('produtos'))
        else:
            flash('Pedido realizado! Entraremos em contato para combinar o pagamento.', 'success')
            return redirect(url_for('index'))

    return render_template('finalizar_compra.html')


@app.route('/pagamento/sucesso/<int:pedido_id>')
def pagamento_sucesso(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Aprovado'; pedido.status = 'Confirmado'
    db.session.commit()
    return render_template('pagamento_resultado.html', status='sucesso', pedido=pedido)


@app.route('/pagamento/falha/<int:pedido_id>')
def pagamento_falha(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Rejeitado'; db.session.commit()
    return render_template('pagamento_resultado.html', status='falha', pedido=pedido)


@app.route('/pagamento/pendente/<int:pedido_id>')
def pagamento_pendente(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Pendente'; db.session.commit()
    return render_template('pagamento_resultado.html', status='pendente', pedido=pedido)


@app.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    try:
        data = request.get_json()
        if data.get('type') == 'payment':
            payment_id = data['data']['id']
            payment = sdk.payment().get(payment_id)["response"]
            pedido_id = payment.get('external_reference')
            if pedido_id:
                pedido = Pedido.query.get(int(pedido_id))
                if pedido:
                    pedido.payment_id = str(payment_id)
                    if payment['status'] == 'approved':
                        pedido.status_pagamento = 'Aprovado'; pedido.status = 'Confirmado'
                    elif payment['status'] == 'rejected':
                        pedido.status_pagamento = 'Rejeitado'
                    else:
                        pedido.status_pagamento = 'Pendente'
                    db.session.commit()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return jsonify({'status': 'error'}), 500


# ── ADMIN — PROTEGIDO ─────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_index():
    return redirect(url_for('admin_produtos'))


@app.route('/admin/produtos')
@login_required
def admin_produtos():
    produtos = Produto.query.all()
    return render_template('admin_produtos.html', produtos=produtos)


@app.route('/admin/produto/novo', methods=['GET', 'POST'])
@login_required
def criar_produto():
    if request.method == 'POST':
        produto = Produto(
            nome=request.form.get('nome'), descricao=request.form.get('descricao'),
            preco=float(request.form.get('preco')), imagem_url=request.form.get('imagem_url'),
            prazo_dias=int(request.form.get('prazo_dias', 7)),
            categoria=request.form.get('categoria'),
            disponivel=request.form.get('disponivel') == 'on'
        )
        db.session.add(produto); db.session.commit()
        flash('Produto criado com sucesso!', 'success')
        return redirect(url_for('admin_produtos'))
    return render_template('form_produto.html', produto=None)


@app.route('/admin/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    produto = Produto.query.get_or_404(id)
    if request.method == 'POST':
        produto.nome = request.form.get('nome')
        produto.descricao = request.form.get('descricao')
        produto.preco = float(request.form.get('preco'))
        produto.imagem_url = request.form.get('imagem_url')
        produto.prazo_dias = int(request.form.get('prazo_dias', 7))
        produto.categoria = request.form.get('categoria')
        produto.disponivel = request.form.get('disponivel') == 'on'
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('admin_produtos'))
    return render_template('form_produto.html', produto=produto)


@app.route('/admin/produto/deletar/<int:id>')
@login_required
def deletar_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto); db.session.commit()
    flash('Produto deletado com sucesso!', 'success')
    return redirect(url_for('admin_produtos'))


@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin_pedidos.html', pedidos=pedidos)


@app.route('/admin/pedido/<int:id>/status/<status>')
@login_required
def alterar_status_pedido(id, status):
    pedido = Pedido.query.get_or_404(id)
    pedido.status = status; db.session.commit()
    flash(f'Status do pedido #{id} alterado para {status}!', 'success')
    return redirect(url_for('admin_pedidos'))


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/produtos')
def api_produtos():
    # Retorna apenas produtos disponíveis — nunca expor indisponíveis publicamente
    produtos = Produto.query.filter_by(disponivel=True).all()
    return jsonify([{'id': p.id, 'nome': p.nome, 'preco': p.preco,
                     'prazo_dias': p.prazo_dias, 'disponivel': p.disponivel}
                    for p in produtos])


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)