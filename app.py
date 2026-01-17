from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "sqlite:///croche_store.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Produto
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    imagem_url = db.Column(db.String(200))
    prazo = db.Column(db.Integer, default=0)
    categoria = db.Column(db.String(50))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    
    produto = db.relationship('Produto', backref='pedidos')

# Criar banco de dados
if os.getenv("RENDER"):
    with app.app_context():
        db.create_all()

# ROTAS
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

@app.route('/carrinho')
def carrinho():
    return render_template('carrinho.html')

@app.route('/finalizar-compra', methods=['GET', 'POST'])
def finalizar_compra():
    if request.method == 'POST':
        produto_id = request.form.get('produto_id')
        quantidade = int(request.form.get('quantidade', 1))
        
        produto = Produto.query.get(produto_id)
        if not produto or produto.estoque < quantidade:
            flash('Produto indisponível ou estoque insuficiente', 'error')
            return redirect(url_for('produtos'))
        
        pedido = Pedido(
            nome_cliente=request.form.get('nome'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            endereco=request.form.get('endereco'),
            produto_id=produto_id,
            quantidade=quantidade,
            total=produto.preco * quantidade
        )
        
        produto.estoque -= quantidade
        db.session.add(pedido)
        db.session.commit()
        
        flash('Pedido realizado com sucesso!', 'success')
        return redirect(url_for('index'))
    
    return render_template('finalizar_compra.html')

# CRUD Admin - Produtos
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
            estoque=int(request.form.get('estoque')),
            categoria=request.form.get('categoria')
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
        produto.estoque = int(request.form.get('estoque'))
        produto.categoria = request.form.get('categoria')
        
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

@app.route('/admin/pedidos')
def admin_pedidos():
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin_pedidos.html', pedidos=pedidos)

if __name__ == '__main__':
    app.run(debug=True)