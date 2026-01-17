# 🧶 Croche by Ju - E-commerce

Sistema completo de e-commerce para venda de produtos artesanais de crochê, desenvolvido com Python Flask, HTML e CSS.

## 📋 Características

- **Homepage atrativa** com identidade visual personalizada
- **Catálogo de produtos** com filtros por categoria
- **Sistema CRUD completo** para gerenciar produtos
- **Carrinho de compras** e finalização de pedidos
- **Painel administrativo** para gestão
- **Banco de dados SQLite** para persistência
- **Design responsivo** e moderno

## 🚀 Tecnologias Utilizadas

- **Backend:** Python 3.8+ com Flask
- **Banco de Dados:** SQLite com SQLAlchemy ORM
- **Frontend:** HTML5, CSS3 (com design inspirado na identidade visual)
- **Tipografia:** Georgia (fonte serifada elegante)
- **Paleta de Cores:** Tons de lavanda (#b19cd9), azul pastel (#9bc4d9) e amarelo suave (#f5d98d)

## 📦 Instalação

### 1. Pré-requisitos

Certifique-se de ter o Python 3.8 ou superior instalado:

```bash
python --version
```

### 2. Clone ou crie a estrutura do projeto

Crie a seguinte estrutura de pastas:

```
croche_by_ju/
│
├── app.py                 # Arquivo principal do Flask
├── requirements.txt       # Dependências do projeto
│
├── templates/            # Templates HTML
│   ├── index.html
│   ├── produtos.html
│   ├── produto_detalhe.html
│   ├── finalizar_compra.html
│   ├── admin_produtos.html
│   └── form_produto.html
│
└── static/               # Arquivos estáticos (opcional)
    └── logo.png          # Logo da marca
```

### 3. Instale as dependências

Crie um arquivo `requirements.txt` com o seguinte conteúdo:

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 4. Configure o banco de dados

O banco de dados será criado automaticamente na primeira execução. Se precisar recriar:

```python
# No terminal Python
from app import app, db
with app.app_context():
    db.create_all()
```

### 5. Execute o servidor

```bash
python app.py
```

O servidor estará disponível em: `http://127.0.0.1:5000`

## 📱 Como Usar

### Para Clientes

1. **Navegue pela Homepage** - Veja produtos em destaque
2. **Explore o Catálogo** - Filtre por categorias
3. **Visualize Detalhes** - Clique em um produto para mais informações
4. **Faça seu Pedido** - Preencha o formulário de compra

### Para Administradores

1. **Acesse o Painel Admin** - `/admin/produtos`
2. **Adicione Produtos** - Clique em "Novo Produto"
3. **Preencha os Dados:**
   - Nome do produto
   - Descrição detalhada
   - Preço
   - Quantidade em estoque
   - Categoria
   - URL da imagem (opcional)
4. **Edite Produtos** - Clique no botão "Editar"
5. **Delete Produtos** - Clique no botão "Deletar" (com confirmação)

## 🎨 Personalização

### Cores da Identidade Visual

As cores principais já estão configuradas no CSS:

- **Lavanda:** `#b19cd9` (cor principal)
- **Azul Pastel:** `#9bc4d9` (secundária)
- **Amarelo Suave:** `#f5d98d` (destaque)
- **Texto:** `#5a4a6a` (cor do texto)

### Adicionar Logo

Coloque a imagem da logo (como a do círculo com o "J") em:
```
static/logo.png
```

## 📊 Estrutura do Banco de Dados

### Tabela: Produto
- `id` - Identificador único
- `nome` - Nome do produto
- `descricao` - Descrição detalhada
- `preco` - Preço (float)
- `imagem_url` - URL da imagem
- `estoque` - Quantidade disponível
- `categoria` - Categoria do produto
- `data_criacao` - Data de cadastro

### Tabela: Pedido
- `id` - Identificador único
- `nome_cliente` - Nome do cliente
- `email` - E-mail do cliente
- `telefone` - Telefone/WhatsApp
- `endereco` - Endereço completo
- `produto_id` - ID do produto (FK)
- `quantidade` - Quantidade comprada
- `total` - Valor total
- `status` - Status do pedido
- `data_pedido` - Data do pedido

## 🔧 Funcionalidades Implementadas

- ✅ Homepage com apresentação da marca
- ✅ Listagem de produtos com filtros
- ✅ Detalhes do produto
- ✅ Sistema de categorias
- ✅ Formulário de compra
- ✅ Painel administrativo
- ✅ CRUD completo de produtos
- ✅ Controle de estoque
- ✅ Visualização de pedidos
- ✅ Design responsivo

## 🎯 Próximos Passos (Melhorias Futuras)

- [ ] Sistema de login/autenticação para admin
- [ ] Upload direto de imagens
- [ ] Integração com gateway de pagamento
- [ ] Sistema de carrinho persistente
- [ ] E-mails automáticos de confirmação
- [ ] Painel de estatísticas de vendas
- [ ] Sistema de avaliações
- [ ] Galeria de imagens por produto

## 🐛 Solução de Problemas

### Erro: "ModuleNotFoundError: No module named 'flask'"
```bash
pip install Flask Flask-SQLAlchemy
```

### Banco de dados não foi criado
```python
from app import app, db
with app.app_context():
    db.create_all()
```

### Imagens não aparecem
- Verifique se a URL da imagem está correta
- Teste o link da imagem em um navegador
- Certifique-se de que a imagem está hospedada publicamente

## 📝 Licença

Este projeto foi desenvolvido para uso comercial da marca Croche by Ju.

## 💝 Contato

Para dúvidas ou sugestões sobre o sistema, entre em contato através dos canais oficiais da Croche by Ju.

---

**Desenvolvido com ❤️ e muitos pontos de crochê**