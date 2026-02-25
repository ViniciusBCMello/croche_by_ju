from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import mercadopago

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///croche_store.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Configuração do Mercado Pago
MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN) if MERCADOPAGO_ACCESS_TOKEN else None

db = SQLAlchemy(app)

# Modelo de Produto
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(200))
    prazo_dias = db.Column(db.Integer, default=7)  # Prazo em dias para entrega
    categoria = db.Column(db.String(50))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    disponivel = db.Column(db.Boolean, default=True)  # Se aceita encomendas
    
    def __repr__(self):
        return f'<Produto {self.nome}>'

# Modelo de Pedido
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
    status_pagamento = db.Column(db.String(20), default='Pendente')  # Pendente, Aprovado, Rejeitado
    payment_id = db.Column(db.String(100))  # ID do pagamento no Mercado Pago
    preference_id = db.Column(db.String(100))  # ID da preferência do Mercado Pago
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    
    produto = db.relationship('Produto', backref='pedidos')

# Criar banco de dados
if os.getenv("RENDER"):
    with app.app_context():
        db.create_all()

# ROTAS PRINCIPAIS
@app.route('/')
def index():
    produtos_destaque = Produto.query.limit(6).all()
    return render_template('index.html', produtos=produtos_destaque)

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
        produto_id = request.form.get('produto_id')
        quantidade = int(request.form.get('quantidade', 1))
        
        produto = Produto.query.get(produto_id)
        if not produto or not produto.disponivel:
            flash('Produto indisponível para encomenda no momento', 'error')
            return redirect(url_for('produtos'))
        
        # Criar pedido
        pedido = Pedido(
            nome_cliente=request.form.get('nome'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            endereco=request.form.get('endereco'),
            produto_id=produto_id,
            quantidade=quantidade,
            total=produto.preco * quantidade
        )
        
        db.session.add(pedido)
        db.session.commit()
        
        # Criar preferência de pagamento no Mercado Pago
        if sdk and MERCADOPAGO_ACCESS_TOKEN:
            try:
                print(f"🔄 Criando preferência de pagamento para pedido #{pedido.id}")
                
                preference_data = {
                    "items": [
                        {
                            "title": produto.nome,
                            "quantity": quantidade,
                            "unit_price": float(produto.preco),
                            "currency_id": "BRL"
                        }
                    ],
                    "payer": {
                        "name": request.form.get('nome'),
                        "email": request.form.get('email')
                    },
                    "back_urls": {
                        "success": url_for('pagamento_sucesso', pedido_id=pedido.id, _external=True),
                        "failure": url_for('pagamento_falha', pedido_id=pedido.id, _external=True),
                        "pending": url_for('pagamento_pendente', pedido_id=pedido.id, _external=True)
                    },
                    "external_reference": str(pedido.id)
                }
                
                print(f"📦 Dados da preferência: {preference_data}")
                
                preference_response = sdk.preference().create(preference_data)
                
                print(f"📥 Resposta completa do MP: {preference_response}")
                
                # Verificar se a resposta tem o formato esperado
                if "response" in preference_response:
                    preference = preference_response["response"]
                elif "id" in preference_response:
                    preference = preference_response
                else:
                    raise Exception(f"Formato de resposta inesperado: {preference_response}")
                
                # Salvar preference_id no pedido
                pedido.preference_id = preference["id"]
                db.session.commit()
                
                # Obter URL de checkout
                init_point = preference.get("init_point") or preference.get("sandbox_init_point")
                
                print(f"✅ Preferência criada! ID: {preference['id']}")
                print(f"🔗 Redirecionando para: {init_point}")
                
                # Redirecionar para o checkout do Mercado Pago
                return redirect(init_point)
                
            except Exception as e:
                print(f"❌ Erro ao criar preferência: {e}")
                print(f"🔍 Tipo do erro: {type(e)}")
                import traceback
                traceback.print_exc()
                flash('Erro ao processar pagamento. Entre em contato conosco.', 'error')
                return redirect(url_for('index'))
        else:
            # Sem Mercado Pago configurado
            print("⚠️ MERCADO PAGO NÃO CONFIGURADO - Configure MERCADOPAGO_ACCESS_TOKEN")
            flash('Pedido realizado! Como o pagamento online não está configurado, entraremos em contato para combinar a forma de pagamento.', 'success')
            return redirect(url_for('index'))
    
    return render_template('finalizar_compra.html')

# Rotas de retorno do pagamento
@app.route('/pagamento/sucesso/<int:pedido_id>')
def pagamento_sucesso(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Aprovado'
    pedido.status = 'Confirmado'
    db.session.commit()
    return render_template('pagamento_resultado.html', status='sucesso', pedido=pedido)

@app.route('/pagamento/falha/<int:pedido_id>')
def pagamento_falha(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Rejeitado'
    db.session.commit()
    return render_template('pagamento_resultado.html', status='falha', pedido=pedido)

@app.route('/pagamento/pendente/<int:pedido_id>')
def pagamento_pendente(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status_pagamento = 'Pendente'
    db.session.commit()
    return render_template('pagamento_resultado.html', status='pendente', pedido=pedido)

# Webhook do Mercado Pago
@app.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    try:
        data = request.get_json()
        
        if data.get('type') == 'payment':
            payment_id = data['data']['id']
            
            # Buscar informações do pagamento
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info["response"]
            
            # Buscar pedido pela external_reference
            pedido_id = payment.get('external_reference')
            if pedido_id:
                pedido = Pedido.query.get(int(pedido_id))
                if pedido:
                    pedido.payment_id = str(payment_id)
                    
                    # Atualizar status baseado no status do pagamento
                    if payment['status'] == 'approved':
                        pedido.status_pagamento = 'Aprovado'
                        pedido.status = 'Confirmado'
                    elif payment['status'] == 'rejected':
                        pedido.status_pagamento = 'Rejeitado'
                    else:
                        pedido.status_pagamento = 'Pendente'
                    
                    db.session.commit()
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return jsonify({'status': 'error'}), 500

# CRUD ADMIN - PRODUTOS
@app.route('/admin/produtos')
def admin_produtos():
    produtos = Produto.query.all()
    return render_template('admin_produtos.html', produtos=produtos)

@app.route('/admin/produto/novo', methods=['GET', 'POST'])
def criar_produto():
    if request.method == 'POST':
        produto = Produto(
            nome=request.form.get('nome'),
            descricao=request.form.get('descricao'),
            preco=float(request.form.get('preco')),
            imagem_url=request.form.get('imagem_url'),
            prazo_dias=int(request.form.get('prazo_dias', 7)),
            categoria=request.form.get('categoria'),
            disponivel=request.form.get('disponivel') == 'on'
        )
        db.session.add(produto)
        db.session.commit()
        flash('Produto criado com sucesso!', 'success')
        return redirect(url_for('admin_produtos'))
    
    return render_template('form_produto.html', produto=None)

@app.route('/admin/produto/editar/<int:id>', methods=['GET', 'POST'])
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
def deletar_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto deletado com sucesso!', 'success')
    return redirect(url_for('admin_produtos'))

# ADMIN - PEDIDOS
@app.route('/admin/pedidos')
def admin_pedidos():
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin_pedidos.html', pedidos=pedidos)

@app.route('/admin/pedido/<int:id>/status/<status>')
def alterar_status_pedido(id, status):
    pedido = Pedido.query.get_or_404(id)
    pedido.status = status
    db.session.commit()
    flash(f'Status do pedido #{id} alterado para {status}!', 'success')
    return redirect(url_for('admin_pedidos'))

# API
@app.route('/api/produtos')
def api_produtos():
    produtos = Produto.query.all()
    return jsonify([{
        'id': p.id,
        'nome': p.nome,
        'preco': p.preco,
        'prazo_dias': p.prazo_dias,
        'disponivel': p.disponivel
    } for p in produtos])

if __name__ == '__main__':
    app.run(debug=True)