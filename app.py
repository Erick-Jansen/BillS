from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import re
import json

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessions'

ARQUIVO_DADOS = 'dados.json'

# Função para carregar os dados
def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'w') as f:
            json.dump({"usuarios": {}}, f)
    with open(ARQUIVO_DADOS, 'r') as f:
        return json.load(f)

# Função para salvar os dados
def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w') as f:
        json.dump(dados, f, indent=4)

# Validação do nome completo
def nome_valido(nome):
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ]+(?: [A-Za-zÀ-ÿ]+)+", nome.strip()))

# Função para converter string valor para float
def valor_str_para_float(valor_str):
    valor_tratado = valor_str.replace('.', '').replace(',', '.')
    return float(valor_tratado)

# Função para converter float para string formatada "x.xxx.xxx,xx"
def valor_float_para_str(valor_float):
    return f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Página inicial
@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('painel'))
    return redirect(url_for('login'))

# Página de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        if not nome_valido(nome):
            return "Nome inválido. Insira nome e sobrenome."

        dados = carregar_dados()

        if email in dados['usuarios']:
            return "Este e-mail já está cadastrado."

        dados['usuarios'][email] = {
            "nome_completo": nome,
            "senha": senha,
            "ganhos": [],
            "gastos": []
        }

        salvar_dados(dados)
        return redirect(url_for('login'))

    return render_template('cadastro.html')

# Página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        dados = carregar_dados()
        usuario = dados['usuarios'].get(email)

        if usuario and usuario['senha'] == senha:
            session['usuario'] = email
            return redirect(url_for('painel'))
        else:
            return "Login inválido."

    return render_template('login.html')

# Página do painel
@app.route('/painel')
def painel():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    dados = carregar_dados()
    usuario = session['usuario']
    nome_completo = dados['usuarios'][usuario]['nome_completo']
    primeiro_nome = nome_completo.strip().split()[0]

    # Lista de dúvidas frequentes
    duvidas = [
        {"pergunta": "Como começar a economizar dinheiro?", "resposta": "Comece controlando seus gastos e definindo metas."},
        {"pergunta": "Qual o melhor jeito de investir?", "resposta": "Depende do seu perfil, mas comece estudando renda fixa e fundos."},
        {"pergunta": "Como criar um fundo de emergência?", "resposta": "Reserve um valor mensal até alcançar de 3 a 6 salários mensais."},
        {"pergunta": "Por que controlar meus gastos?", "resposta": "Porque você só melhora o que você mede."},
        {"pergunta": "Cartão de crédito é vilão?", "resposta": "Não, se usado com planejamento e controle."},
        {"pergunta": "Vale a pena usar planilhas?", "resposta": "Sim, elas ajudam a visualizar entradas e saídas."},
        {"pergunta": "Como organizar meu salário?", "resposta": "Use a regra 50/30/20: 50% necessidades, 30% desejos, 20% investimentos."}
    ]

    return render_template('painel.html', primeiro_nome=primeiro_nome, duvidas=duvidas)

# Logout
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))


@app.route('/transacoes', methods=['GET', 'POST'])
def transacoes():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    dados = carregar_dados()
    usuario = session['usuario']
    usuario_data = dados['usuarios'][usuario]

    if request.method == 'POST':
        tipo = request.form.get('tipo')  # 'ganho' ou 'gasto'
        descricao = request.form.get('descricao', '').strip()
        valor = request.form.get('valor', '').strip()
        data = request.form.get('data', '').strip()

        # Validação da data
        if data:
            if not re.fullmatch(r'\d{2}/\d{2}/\d{4}', data):
                flash('Data inválida. Use o formato dd/mm/aaaa.', 'erro')
                return redirect(url_for('transacoes'))
            try:
                dia, mes, ano = map(int, data.split('/'))
                data_obj = datetime(ano, mes, dia)
            except ValueError:
                flash('Data inválida. Por favor, corrija.', 'erro')
                return redirect(url_for('transacoes'))

            # Limite máximo: 1 ano a partir da data atual
            limite_max = datetime.now() + timedelta(days=365)
            if data_obj > limite_max:
                flash('Data não pode ser maior que 1 ano a partir de hoje.', 'erro')
                return redirect(url_for('transacoes'))
        else:
            data_obj = None

        # Validação do valor
        try:
            valor_float = valor_str_para_float(valor)
            if valor_float < 0 or valor_float > 1_000_000_000:
                flash('Valor deve ser entre 0 e 1 bilhão.', 'erro')
                return redirect(url_for('transacoes'))
            valor_formatado = valor_float_para_str(valor_float)
        except:
            flash('Valor inválido. Use formato correto, ex: 1.000,45', 'erro')
            return redirect(url_for('transacoes'))

        registro = {
            'descricao': descricao,
            'valor': valor_formatado,
            'data': data if data else '',
        }

        if tipo == 'ganho':
            usuario_data['ganhos'].append(registro)
        elif tipo == 'gasto':
            usuario_data['gastos'].append(registro)
        else:
            flash('Tipo inválido.', 'erro')
            return redirect(url_for('transacoes'))

        salvar_dados(dados)
        flash(f'{tipo.capitalize()} adicionado com sucesso!', 'sucesso')
        return redirect(url_for('transacoes'))

    # Função para ordenar por data (mais recente primeiro)
    def chave_data(item):
        try:
            return datetime.strptime(item['data'], '%d/%m/%Y')
        except:
            return datetime.min

    ganhos = sorted(usuario_data['ganhos'], key=chave_data, reverse=True)
    gastos = sorted(usuario_data['gastos'], key=chave_data, reverse=True)

    # Cálculo do saldo total e do mês atual
    saldo_total = 0.0
    saldo_mes = 0.0
    hoje = datetime.now()

    for g in usuario_data['ganhos']:
        try:
            v = valor_str_para_float(g['valor'])
            saldo_total += v
            if g['data']:
                dt = datetime.strptime(g['data'], '%d/%m/%Y')
                if dt.year == hoje.year and dt.month == hoje.month:
                    saldo_mes += v
        except:
            pass

    for g in usuario_data['gastos']:
        try:
            v = valor_str_para_float(g['valor'])
            saldo_total -= v
            if g['data']:
                dt = datetime.strptime(g['data'], '%d/%m/%Y')
                if dt.year == hoje.year and dt.month == hoje.month:
                    saldo_mes -= v
        except:
            pass

    saldo_total_str = valor_float_para_str(saldo_total)
    saldo_mes_str = valor_float_para_str(saldo_mes)

    return render_template('transacoes.html', ganhos=ganhos, gastos=gastos,
                           saldo_total=saldo_total_str, saldo_mes=saldo_mes_str)


@app.route('/editar_transacao/<tipo>/<int:index>', methods=['POST'])
def editar_transacao(tipo, index):
    if 'usuario' not in session:
        flash('Você precisa estar logado.', 'erro')
        return redirect(url_for('login'))

    if tipo not in ['ganho', 'gasto']:
        flash('Tipo de transação inválido.', 'erro')
        return redirect(url_for('transacoes'))

    descricao = request.form.get('descricao', '').strip()
    valor = request.form.get('valor', '').strip()
    data = request.form.get('data', '').strip()

    if not descricao:
        flash('A descrição não pode estar vazia.', 'erro')
        return redirect(url_for('transacoes'))

    # Validação da data
    if data:
        if not re.fullmatch(r'\d{2}/\d{2}/\d{4}', data):
            flash('Data inválida. Use o formato dd/mm/aaaa.', 'erro')
            return redirect(url_for('transacoes'))
        try:
            dia, mes, ano = map(int, data.split('/'))
            data_obj = datetime(ano, mes, dia)
        except ValueError:
            flash('Data inválida. Por favor, corrija.', 'erro')
            return redirect(url_for('transacoes'))

        limite_max = datetime.now() + timedelta(days=365)
        if data_obj > limite_max:
            flash('Data não pode ser maior que 1 ano a partir de hoje.', 'erro')
            return redirect(url_for('transacoes'))
    else:
        data_obj = None

    # Validação do valor
    try:
        valor_float = valor_str_para_float(valor)
        if valor_float < 0 or valor_float > 1_000_000_000:
            flash('Valor deve ser entre 0 e 1 bilhão.', 'erro')
            return redirect(url_for('transacoes'))
        valor_formatado = valor_float_para_str(valor_float)
    except:
        flash('Valor inválido. Use o formato correto, ex: 1.000,45', 'erro')
        return redirect(url_for('transacoes'))

    dados = carregar_dados()
    usuario = session['usuario']
    transacoes = dados['usuarios'][usuario][f'{tipo}s']

    if index < 0 or index >= len(transacoes):
        flash('Transação não encontrada.', 'erro')
        return redirect(url_for('transacoes'))

    transacoes[index] = {
        'descricao': descricao,
        'valor': valor_formatado,
        'data': data if data else ''
    }

    salvar_dados(dados)
    flash(f'{tipo.capitalize()} editado com sucesso!', 'sucesso')
    return redirect(url_for('transacoes'))




@app.route('/excluir_transacao/<tipo>/<int:index>', methods=['POST'])
def excluir_transacao(tipo, index):
    if 'usuario' not in session:
        flash('Você precisa estar logado.', 'erro')
        return redirect(url_for('login'))

    if tipo not in ['ganho', 'gasto']:
        flash('Tipo de transação inválido.', 'erro')
        return redirect(url_for('transacoes'))

    dados = carregar_dados()
    usuario = session['usuario']
    transacoes = dados['usuarios'][usuario][f'{tipo}s']

    if index < 0 or index >= len(transacoes):
        flash('Transação não encontrada.', 'erro')
        return redirect(url_for('transacoes'))

    transacoes.pop(index)
    salvar_dados(dados)
    flash(f'{tipo.capitalize()} excluído com sucesso!', 'sucesso')
    return redirect(url_for('transacoes'))


if __name__ == '__main__':
    app.run(debug=True)
