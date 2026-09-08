# Conversor DANFE

**Página do projeto:** https://ogabrieltech.com.br/projetos/conversor-danfe.html  
**Repositório:** https://github.com/ogabrieltech/conversor-danfe

Aplicativo desktop em Python para converter XMLs autorizados de **NF-e modelo 55** em arquivos DANFE PDF.

O projeto processa arquivos localmente, aceita XML, ZIP ou pastas inteiras e gera um relatório CSV com o resultado de cada documento.

## Funcionalidades

- Conversão de XML de NF-e modelo 55 para DANFE PDF
- Processamento de um ou vários XMLs
- Leitura de ZIPs contendo XMLs
- Varredura recursiva de pastas
- Validação do modelo e do protocolo de autorização
- Detecção de NF-e duplicada no mesmo lote
- Preservação de PDFs existentes por padrão
- Opção para consolidar o lote em um único PDF
- Nomeação automática dos arquivos por número da NF e destinatário
- Relatório CSV de arquivos gerados, ignorados e com erro
- Interface gráfica em Tkinter
- Modo de linha de comando
- Processamento local, sem envio dos XMLs para serviços externos

## Tecnologias

- Python 3.12
- Tkinter
- BrazilFiscalReport
- pypdf
- PyInstaller
- XML / `xml.etree.ElementTree`

## Estrutura

```text
conversor-danfe/
├── conversor_danfe.py
├── INSTALAR.cmd
├── requirements.txt
├── requirements-build.txt
├── tests/
│   └── test_conversor_danfe.py
├── docs/
│   └── index.html
├── THIRD_PARTY_LICENSES.md
├── LICENSE
└── README.md
```

## Instalação no Windows

### Opção 1 — instalador local

1. Baixe ou clone o repositório.
2. Execute `INSTALAR.cmd`.
3. O script cria um ambiente temporário, instala as dependências e gera `Conversor DANFE.exe`.
4. Um atalho é criado na Área de Trabalho.

O instalador usa Python 3.12 e `winget` quando necessário.

### Opção 2 — executar com Python

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python conversor_danfe.py
```

## Uso pela interface

1. Selecione arquivos XML/ZIP ou uma pasta.
2. Escolha a pasta de destino.
3. Opcionalmente selecione uma logo e habilite a união dos PDFs.
4. Clique em **GERAR DANFEs**.

Por padrão, os arquivos são salvos em uma pasta `DANFEs` próxima à origem.

## Uso pelo terminal

```bash
python conversor_danfe.py --cli notas.xml
```

Processar uma pasta inteira:

```bash
python conversor_danfe.py --cli ./xmls --output ./saida
```

Criar também um PDF consolidado:

```bash
python conversor_danfe.py --cli ./xmls --merge
```

Substituir PDFs existentes:

```bash
python conversor_danfe.py --cli ./xmls --overwrite
```

## Regras de validação

O conversor aceita apenas documentos que atendam aos critérios abaixo:

- estrutura de NF-e (`NFe` ou `nfeProc`);
- modelo fiscal `55`;
- protocolo com status de autorização suportado;
- XML com tamanho máximo de 50 MB por documento.

Arquivos que não atendem às regras são ignorados e registrados no relatório de conversão.

## Privacidade

O processamento ocorre no computador do usuário. O aplicativo não envia XMLs, dados fiscais ou PDFs para APIs ou serviços web.

## Testes

Os testes cobrem a leitura dos principais campos da NF-e, validação do modelo fiscal e tratamento de nomes de arquivo.

```bash
python -m unittest discover -s tests -v
```

## Observação fiscal

O DANFE é uma representação auxiliar da NF-e. O XML autorizado continua sendo o documento fiscal eletrônico e deve ser armazenado conforme as obrigações aplicáveis.

## Licença

O código deste repositório é disponibilizado sob a licença MIT. As bibliotecas utilizadas mantêm suas próprias licenças; consulte [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

## Autor

**Gabriel Santos**  
Analista de Sistemas — Análise e Desenvolvimento de Sistemas

- GitHub: https://github.com/ogabrieltech
- LinkedIn: https://linkedin.com/in/gabriel-santos-708aa1154
