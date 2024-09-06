import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import tempfile
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import xml.etree.ElementTree as ET
import re  # Adicione isso no início do seu código
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from reportlab.lib.units import inch

# Inicialização da variável global
cargas_data = {}
infos = []

# Inicialização da variável global
warning_active = False
last_warning_time = {}
warning_interval = 5  # Intervalo entre avisos em segundos

def load_product_data():
    try:
        with open("produtos.json", "r") as file:
            data = json.load(file)
            return {code.lstrip('0'): details for code, details in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

product_data = load_product_data()

def add_barcode():
    carga_number = carga_entry_add.get()
    barcode = barcode_entry.get().lstrip('0')  # Remover zeros à esquerda
    quantity = quantity_entry.get()  # Obter quantidade do novo campo
    
    if carga_number and barcode:
        # Verifica se o código de barras tem exatamente 7 dígitos
        if len(barcode) != 7:
            messagebox.showwarning("Código de Barras Incorreto", "O código de barras deve ter exatamente 7 dígitos.")
            barcode_entry.delete(0, tk.END)
            quantity_entry.delete(0, tk.END)
            return

        if carga_number not in cargas_data:
            cargas_data[carga_number] = []

        description = product_data.get(barcode, {}).get('Descrição', 'Descrição não encontrada')
        
        # Se quantidade não for fornecida, definir como '1'
        if not quantity.isdigit():
            quantity = '1'

        cargas_data[carga_number].append((barcode, description, quantity))

        display_area.config(state='normal')
        formatted_text = f"Código: {barcode:<10} | Descrição: {description:<30} | Quantidade: {quantity}\n"
        display_area.insert(tk.END, formatted_text)
        display_area.config(state='disabled')
        
        display_area.see(tk.END)
        barcode_entry.delete(0, tk.END)
        quantity_entry.delete(0, tk.END)  # Limpar o campo de quantidade

def auto_add_barcode(event=None):
    
    if event and event.keysym in ('Return', 'Tab', 'Enter', 'space'):
        return

    def check_barcode_after_delay():
        barcode = barcode_entry.get().lstrip('0')
        quantity = quantity_entry.get()

        if not barcode:
            return

        if not barcode.isnumeric():
            show_warning("Código de Barras Inválido", "O código de barras não pode conter caracteres alfabéticos.", barcode)
            return  

        if len(barcode) == 7:
            if carga_entry_add.get():
                add_barcode()
            last_warning_time.pop(barcode, None)  # Reset warning status for valid barcode

        elif len(barcode) > 7:
            show_warning("Código de Barras Incorreto", "O código de barras deve ter exatamente 7 dígitos.", barcode)
            barcode_entry.delete(0, tk.END)  # Limpar o campo de código de barras
            quantity_entry.delete(0, tk.END)  # Limpar o campo de quantidade

        # Reset warning status for empty barcode or after handling an invalid barcode
        if not barcode or len(barcode) > 7:
            last_warning_time.pop(barcode, None)

    barcode_entry.after(1000, check_barcode_after_delay)

def show_warning(title, message, barcode):
    global warning_active
    
    current_time = time.time()
    last_warning = last_warning_time.get(barcode, 0)
    
    if (current_time - last_warning) > warning_interval and not warning_active:
        warning_active = True
        
        # Função para limpar os campos
        def on_ok():
            global warning_active
            warning_active = False
            barcode_entry.delete(0, tk.END)  # Limpar o campo de código de barras
            quantity_entry.delete(0, tk.END)  # Limpar o campo de quantidade
        
        # Exibindo o aviso
        messagebox.showwarning(title, message)
        
        # Agendando a chamada da função on_ok após um atraso
        root.after(100, on_ok)
        
        # Atualizar o tempo do último aviso
        last_warning_time[barcode] = current_time

def confirm_consult():
    carga_number = consult_entry.get()
    if carga_number in cargas_data:
        consult_display_area.config(state='normal')
        consult_display_area.delete(1.0, tk.END)
        for barcode, description, quantity in cargas_data[carga_number]:
            formatted_text = f"Código: {barcode:<10} | Descrição: {description:<30} | Quantidade: {quantity}\n"
            consult_display_area.insert(tk.END, formatted_text)
        consult_display_area.config(state='disabled')
        consult_entry.delete(0, tk.END)  # Limpar o número de carga
    else:
        messagebox.showwarning("Carga Não Encontrada", "Esse número de carga não foi encontrado.")
        consult_display_area.config(state='normal')
        consult_display_area.delete(1.0, tk.END)  # Limpar o display de informações
        consult_display_area.config(state='disabled')

# Função para salvar os dados do código de barras
def save_barcode_data():
    carga_number = carga_entry_add.get()
    if carga_number in cargas_data:
        # Agrupar e calcular as quantidades
        aggregated_data = {}

        # Processar dados da tela de conferência
        for barcode, description, quantity in cargas_data[carga_number]:
            if barcode in aggregated_data:
                aggregated_data[barcode]['QTD CONFERÊNCIA'] += int(quantity)
            else:
                aggregated_data[barcode] = {
                    'Descrição': description,
                    'QTD CONFERÊNCIA': int(quantity),
                    'QTD XML': 0  # Inicializa a quantidade do XML como 0
                }

        # Atualizar a quantidade do XML com os dados do JSON
        with open('informacoes_encontradas.json', 'r') as f:
            json_data = json.load(f)

        for item in json_data:
            if item['Carga'] == carga_number:
                barcode = item['Cod Prod']
                quantity_xml = int(float(item['Quantidade']))  # Converter quantidade para inteiro
                if barcode in aggregated_data:
                    aggregated_data[barcode]['QTD XML'] += quantity_xml
                else:
                    aggregated_data[barcode] = {
                        'Descrição': item['Descrição'],
                        'QTD CONFERÊNCIA': 0,
                        'QTD XML': quantity_xml
                    }

        # Gerar o PDF com os dados agrupados
        generate_and_save_pdf(carga_number, aggregated_data)

        carga_entry_add.delete(0, tk.END)  # Limpar o número de carga
        display_area.config(state='normal')
        display_area.delete(1.0, tk.END)  # Limpar o display
        display_area.config(state='disabled')
        messagebox.showinfo("Dados Salvos", "Os dados foram salvos com sucesso!")
    else:
        messagebox.showwarning("Sem Dados", "Não há dados para salvar.")

# Função para gerar e salvar o PDF
# Função para gerar e salvar o PDF
import os

def generate_and_save_pdf(carga_number, aggregated_data):
    # Caminho temporário para o PDF
    pdf_path = os.path.join(tempfile.gettempdir(), f"relatorio_{carga_number}.pdf")

    # Configuração do documento
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Adicionar imagem ao cabeçalho
    image_path = "jetta_logo.png"  # Substitua pelo caminho da sua imagem
    try:
        logo = Image(image_path)
        logo.drawHeight = 1 * inch  # Ajuste a altura da imagem
        logo.drawWidth = 2 * inch  # Ajuste a largura da imagem
        elements.append(logo)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar a imagem: {e}")
        return

    # Título do relatório
    title = Paragraph(f"Relatório da Carga: {carga_number}", styles['Title'])
    elements.append(title)

    # Dados em formato de tabela, incluindo as novas colunas "Faltou" e "Sobrou"
    table_data = [["Código", "Descrição", "QTD CONFERÊNCIA", "QTD XML", "Faltou", "Sobrou"]]
    for barcode, details in sorted(aggregated_data.items()):  # Ordenar os dados pelo código de barras
        qtd_conferencia = details['QTD CONFERÊNCIA']
        qtd_xml = details['QTD XML']
        diferenca = qtd_xml - qtd_conferencia  # Calcular a diferença

        # Determinar o valor a ser colocado nas colunas "Faltou" e "Sobrou"
        if diferenca > 0:
            faltou = diferenca
            sobrou = 0
        else:
            faltou = 0
            sobrou = abs(diferenca)

        # Adicionar os dados na tabela, incluindo as novas colunas
        table_data.append([barcode, details['Descrição'],
                           str(qtd_conferencia),
                           str(qtd_xml),
                           str(faltou),  # Valor na coluna "Faltou"
                           str(sobrou)])  # Valor na coluna "Sobrou"

    # Estilização da tabela
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Construção do PDF
    try:
        doc.build(elements)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao gerar o PDF: {e}")
        return

    # Definir o local padrão na Área de Trabalho
    default_save_path = os.path.join(os.path.expanduser("~"), "Desktop", "Relatorios", f"relatorio_{carga_number}.pdf")

    # Criar a pasta "Relatorios" se ela não existir
    os.makedirs(os.path.dirname(default_save_path), exist_ok=True)

    # Opção de salvar o relatório
    save_option = messagebox.askyesno("Salvar Relatório", "Deseja salvar o relatório gerado?")
    if save_option:
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"relatorio_{carga_number}.pdf",
            initialdir=os.path.dirname(default_save_path)  # Diretório padrão
        )
        if save_path:
            try:
                os.rename(pdf_path, save_path)
                messagebox.showinfo("Relatório Salvo", f"Relatório salvo como: {save_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar o PDF: {e}")
                os.remove(pdf_path)
        else:
            os.remove(pdf_path)
    else:
        os.remove(pdf_path)

def print_consult_report():
    carga_number = consult_entry.get()
    if carga_number in cargas_data:
        generate_and_save_pdf(carga_number, cargas_data[carga_number])
    else:
        messagebox.showwarning("Carga Não Encontrada", "Esse número de carga não foi encontrado.")

def show_first_screen():
    add_frame.pack_forget()
    consult_frame.pack_forget()
    import_frame.pack_forget()
    first_screen_frame.pack(fill='both', expand=True)

def show_add_screen():
    first_screen_frame.pack_forget()
    import_frame.pack_forget()
    consult_frame.pack_forget()
    add_frame.pack(fill='both', expand=True)

def show_consult_screen():
    first_screen_frame.pack_forget()
    import_frame.pack_forget()
    add_frame.pack_forget()
    consult_frame.pack(fill='both', expand=True)

def show_import_screen():
    first_screen_frame.pack_forget()
    add_frame.pack_forget()
    consult_frame.pack_forget()
    import_frame.pack(fill='both', expand=True)

def go_back_from_add():
    add_frame.pack_forget()
    show_first_screen()

def go_back_from_consult():
    consult_frame.pack_forget()
    show_first_screen()

def go_back_from_import():
    import_frame.pack_forget()
    show_first_screen()

def close_application():
    root.destroy()

def load_files():
    global infos  
    numero_carga = carga_entry_import.get()
    file_paths = filedialog.askopenfilenames(filetypes=[("XML files", "*.xml")])
    if file_paths:
        infos = []  
        formatted_texts = []  

        for file_path in file_paths:
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                namespace = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

                nf_element = root.find('.//nfe:infNFe/nfe:ide/nfe:cNF', namespace)
                nf_number = nf_element.text if nf_element is not None else "Número da NF não encontrado"

                produtos = root.findall('.//nfe:det/nfe:prod', namespace)
                for produto in produtos:
                    nome_produto = produto.find('nfe:xProd', namespace)
                    quantidade = produto.find('nfe:qCom', namespace)
                    codigo_produto = produto.find('nfe:cProd', namespace)

                    info = {
                        'Carga': numero_carga,
                        'Código': nf_number,
                        'Cod Prod': codigo_produto.text.lstrip('0') if codigo_produto is not None else 'N/A',
                        'Quantidade': quantidade.text if quantidade is not None else 'N/A',
                        'Descrição': nome_produto.text if nome_produto is not None else 'N/A'
                    }
                    infos.append(info)

                    formatted_text = f"Carga: {info['Carga']} | Código: {info['Código']} | Cod Prod: {info['Cod Prod']} | Quantidade: {info['Quantidade']} | Descrição: {info['Descrição']}\n"
                    formatted_texts.append(formatted_text)
            except Exception as e:
                formatted_texts.append(f"Erro ao processar o arquivo {file_path}: {e}")

        import_display_area.config(state='normal')
        import_display_area.delete(1.0, tk.END)
        import_display_area.insert(tk.END, ''.join(formatted_texts))
        import_display_area.config(state='disabled')

def save_to_json():
    global infos 
    numero_carga = carga_entry_import.get()  # Obtém o número da carga

    if not numero_carga:
        messagebox.showwarning("Campo Obrigatório", "Por favor, preencha o número da carga antes de salvar.")
        return

    if infos:
        data_filename = "informacoes_encontradas.json"
        products_filename = "produtos.json"

        if os.path.exists(data_filename):
            with open(data_filename, "r") as file:
                try:
                    existing_data = json.load(file)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        existing_data.extend(infos)

        with open(data_filename, "w") as file:
            json.dump(existing_data, file, indent=4)

        product_data.update({info['Cod Prod']: {'Descrição': info['Descrição']} for info in infos if info['Cod Prod']})

        with open(products_filename, "w") as file:
            json.dump(product_data, file, indent=4)

        infos = []  # Limpa a lista de informações

        # Limpa o número da carga e o display
        carga_entry_import.delete(0, tk.END)
        import_display_area.config(state='normal')
        import_display_area.delete(1.0, tk.END)
        import_display_area.config(state='disabled')

        messagebox.showinfo("Dados Salvos", "Dados importados e salvos com sucesso!")

root = tk.Tk()
root.title("Controle de Entrada Cacau")

# Obter as dimensões da tela
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Definir a janela para ocupar a tela inteira, mas sem o modo de tela cheia
root.geometry(f"{screen_width}x{screen_height}-1+0")

# Manter a barra de tarefas visível
root.overrideredirect(False)

first_screen_frame = tk.Frame(root)
tk.Label(first_screen_frame, text="Tela Principal", font=("Helvetica", 16)).pack(pady=10)

import_button = tk.Button(first_screen_frame, text="Importar XML", command=show_import_screen)
import_button.pack(pady=5)
add_button = tk.Button(first_screen_frame, text="Adicionar Código de Barras", command=show_add_screen)
add_button.pack(pady=5)
consult_button = tk.Button(first_screen_frame, text="Consultar Carga", command=show_consult_screen)
consult_button.pack(pady=5)
exit_button = tk.Button(first_screen_frame, text="Sair", command=close_application)
exit_button.pack(pady=5)

# Tela de Adição de Código de Barras
add_frame = tk.Frame(root)

add_controls_frame = tk.Frame(add_frame)
add_controls_frame.pack(pady=10, side='top')  # Adicionado para botões na parte superior

tk.Label(add_controls_frame, text="Número da Carga:", font=("Helvetica", 14)).grid(row=0, column=0, padx=5, pady=5)
carga_entry_add = tk.Entry(add_controls_frame, font=("Helvetica", 14))
carga_entry_add.grid(row=0, column=1, padx=5, pady=5)

tk.Label(add_controls_frame, text="Quantidade:", font=("Helvetica", 14)).grid(row=1, column=0, padx=5, pady=5)
quantity_entry = tk.Entry(add_controls_frame, font=("Helvetica", 14))
quantity_entry.grid(row=1, column=1, padx=5, pady=5)

tk.Label(add_controls_frame, text="Código de Barras:", font=("Helvetica", 14)).grid(row=1, column=2, padx=5, pady=5)
barcode_entry = tk.Entry(add_controls_frame, font=("Helvetica", 14))
barcode_entry.grid(row=1, column=3, padx=5, pady=5)

save_button = tk.Button(add_controls_frame, text="Salvar", command=save_barcode_data)
save_button.grid(row=2, column=0, padx=5, pady=5)

back_button_add = tk.Button(add_controls_frame, text="Voltar", command=go_back_from_add)
back_button_add.grid(row=2, column=1, padx=5, pady=5)

display_area = tk.Text(add_frame, font=("Helvetica", 14), height=20, width=100, state='disabled')
display_area.pack(pady=10, padx=10)

# Vincule a função auto_add_barcode ao evento KeyRelease no campo de código de barras
barcode_entry.bind('<KeyRelease>', auto_add_barcode)

# Tela de Consulta de Carga
consult_frame = tk.Frame(root)

consult_controls_frame = tk.Frame(consult_frame)
consult_controls_frame.pack(pady=10, side='top')  # Adicionado para botões na parte superior

tk.Label(consult_controls_frame, text="Número da Carga:", font=("Helvetica", 14)).grid(row=0, column=0, padx=5, pady=5)
consult_entry = tk.Entry(consult_controls_frame, font=("Helvetica", 14))
consult_entry.grid(row=0, column=1, padx=5, pady=5)

consult_button = tk.Button(consult_controls_frame, text="Consultar", command=confirm_consult)
consult_button.grid(row=1, column=0, padx=5, pady=5)

print_button = tk.Button(consult_controls_frame, text="Gerar PDF", command=print_consult_report)
print_button.grid(row=1, column=1, padx=5, pady=5)

back_button_consult = tk.Button(consult_controls_frame, text="Voltar", command=go_back_from_consult)
back_button_consult.grid(row=1, column=2, padx=5, pady=5)

consult_display_area = tk.Text(consult_frame, font=("Helvetica", 14), height=20, width=100, state='disabled')
consult_display_area.pack(pady=10, padx=10)

# Tela de Importação de XML
import_frame = tk.Frame(root)

import_controls_frame = tk.Frame(import_frame)
import_controls_frame.pack(pady=10, side='top')  # Adicionado para botões na parte superior

tk.Label(import_controls_frame, text="Número da Carga:", font=("Helvetica", 14)).grid(row=0, column=0, padx=5, pady=5)
carga_entry_import = tk.Entry(import_controls_frame, font=("Helvetica", 14))
carga_entry_import.grid(row=0, column=1, padx=5, pady=5)

import_button = tk.Button(import_controls_frame, text="Carregar XMLs", command=load_files)
import_button.grid(row=1, column=0, padx=5, pady=5)

save_button_import = tk.Button(import_controls_frame, text="Salvar XMLs", command=save_to_json)
save_button_import.grid(row=1, column=1, padx=5, pady=5)

back_button_import = tk.Button(import_controls_frame, text="Voltar", command=go_back_from_import)
back_button_import.grid(row=1, column=2, padx=5, pady=5)

import_display_area = tk.Text(import_frame, font=("Helvetica", 14), height=20, width=100, state='disabled')
import_display_area.pack(pady=10, padx=10)

show_first_screen()
root.mainloop()
print('Aplicativo Finalizado')