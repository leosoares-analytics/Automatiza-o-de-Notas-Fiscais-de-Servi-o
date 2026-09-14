# 🧾 Automação de Notas Fiscais

> **Pipeline automatizado para recebimento, extração, validação, armazenamento e acompanhamento de Notas Fiscais (NFs).**

Este projeto apresenta uma solução de automação para centralizar o recebimento de notas fiscais enviadas por e-mail, extrair informações dos documentos, armazená-las em um banco PostgreSQL e disponibilizar um painel para acompanhamento das aprovações.

O projeto foi desenvolvido como um **MVP utilizando dados e documentos fictícios**, com foco em automação de processos, integração entre sistemas, tratamento de dados e aplicação de conceitos de Engenharia de Dados e IA.

---

## 🎯 Objetivo

O processo tradicional de recebimento de NFs pode envolver diversas tarefas manuais:

* Receber e-mails em diferentes caixas;
* Baixar anexos;
* Abrir arquivos PDF/XML;
* Digitar informações em planilhas;
* Conferir dados;
* Identificar notas duplicadas;
* Encaminhar documentos para aprovação;
* Acompanhar manualmente o status financeiro.

A proposta deste projeto é automatizar as etapas operacionais e centralizar as informações em uma única esteira.

A automação **não substitui a decisão humana**: o gestor continua responsável pela aprovação e o financeiro pelo pagamento.

---

## 🏗️ Arquitetura da Solução

```text
                    ┌─────────────────────┐
                    │     Outlook         │
                    │   Caixa de E-mail   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │        n8n           │
                    │ Orquestração do      │
                    │ processo             │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
              ┌───────────┐        ┌───────────┐
              │    PDF    │        │    XML    │
              │  Extração │        │  Extração │
              └─────┬─────┘        └─────┬─────┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │   IA / Gemini       │
                    │ Estruturação dos    │
                    │ dados extraídos     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │        Neon         │
                    │                     │
                    │  Persistência +     │
                    │  controle de        │
                    │  duplicidade        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Streamlit       │
                    │                     │
                    │ Dashboard de        │
                    │ acompanhamento      │
                    └─────────────────────┘
```

---

## 🔄 Fluxo do Processo

### 1. Recebimento do e-mail

O workflow consulta a caixa de e-mail e identifica mensagens relacionadas a notas fiscais.

São considerados assuntos que contenham termos como:

```text
NF
nf
Nota Fiscal
```

O processo também permite trabalhar com anexos em diferentes formatos.

---

### 2. Identificação do documento

O n8n verifica os anexos recebidos e direciona o processamento de acordo com o tipo de arquivo:

```text
PDF → Extração de texto → IA → Dados estruturados

XML → Leitura do XML → IA → Dados estruturados
```

O workflow utiliza nodes específicos para leitura dos arquivos PDF e XML.

---

### 3. Extração das informações

A solução utiliza um modelo de IA para transformar o conteúdo dos documentos em dados estruturados.

Entre os principais campos extraídos estão:

| Campo                  | Descrição             |
| ---------------------- | --------------------- |
| `data_emissao`         | Data de emissão da NF |
| `valor`                | Valor total da nota   |
| `numero_protocolo`     | Identificador da nota |
| `empresa_destinataria` | Empresa destinatária  |
| `fornecedor`           | Fornecedor/emitente   |

Isso reduz a necessidade de digitação manual e permite que documentos com estruturas diferentes sejam processados de forma padronizada.

---

## 🗄️ Persistência dos Dados

Após a extração e tratamento, os dados são armazenados em um banco PostgreSQL hospedado no **Neon**.

A tabela principal contém informações como:

```text
data_emissao
valor
numero_protocolo
empresa_destinataria
fornecedor
status_gerente
status_financeiro
data_gerente
data_financeiro
data_vencimento
```

O banco também é utilizado como mecanismo de controle de duplicidade.

### 🔐 Controle de duplicidade

O `numero_protocolo` funciona como identificador da nota.

Caso uma mesma NF seja recebida novamente, o banco impede o lançamento duplicado.

```text
Nova NF
   │
   ▼
Extrair protocolo
   │
   ▼
Verificar banco
   │
   ├── Já existe → Rejeitar duplicidade
   │
   └── Não existe → Inserir registro
```

---

## 📊 Dashboard

Os dados armazenados são disponibilizados através de um dashboard desenvolvido em **Streamlit**.

O painel permite acompanhar:

* Notas pendentes;
* Aprovações do gestor;
* Status financeiro;
* Valores das notas;
* Datas de emissão;
* Datas de vencimento;
* Fornecedores;
* Empresas destinatárias.

O objetivo é substituir o acompanhamento descentralizado por e-mails e planilhas por uma visualização centralizada do processo.

---

## 👥 Human-in-the-Loop

Um dos princípios importantes deste projeto é que **a automação não toma decisões financeiras de forma autônoma**.

### O sistema automatiza:

* Recebimento;
* Identificação;
* Leitura dos documentos;
* Extração dos dados;
* Organização;
* Persistência;
* Detecção de duplicidades;
* Notificações de erros.

### As pessoas continuam responsáveis por:

* Conferência dos dados;
* Aprovação da despesa;
* Pagamento da nota.

```text
Automação
    │
    ├── Recebe
    ├── Extrai
    ├── Valida
    ├── Armazena
    └── Organiza
             │
             ▼
        👤 Gestor
        Aprovação
             │
             ▼
        👤 Financeiro
         Pagamento
```

Essa abordagem reduz tarefas repetitivas sem retirar do processo as decisões que exigem responsabilidade humana.

---

## ⚠️ Tratamento de Exceções

O workflow também considera situações fora do fluxo esperado.

### E-mail sem anexo

Quando um e-mail identificado como NF não possui anexo, é enviada uma notificação com o link da mensagem original para facilitar a correção.

### Documento duplicado

Quando uma nota já cadastrada é recebida novamente, o banco impede a duplicidade através do identificador da nota.

### Falha de conexão

Em caso de problemas de conexão ou indisponibilidade do banco, o processo deve ser tratado como uma exceção operacional e encaminhado ao responsável técnico.

---

## 🛠️ Tecnologias

| Tecnologia            | Utilização                                         |
| --------------------- | -------------------------------------------------- |
| **n8n**               | Orquestração e automação do workflow               |
| **Microsoft Outlook** | Recebimento dos documentos                         |
| **Google Gemini**     | Extração/estruturação de informações               |
| **PostgreSQL**        | Persistência dos dados                             |
| **Neon**              | Hospedagem do PostgreSQL                           |
| **Streamlit**         | Dashboard e visualização                           |
| **Python**            | Desenvolvimento do dashboard e tratamento de dados |
| **Git/GitHub**        | Versionamento e documentação                       |

---

## 📁 Estrutura sugerida do projeto

```text
automacao-notas-fiscais/
│
├── n8n/
│   └── workflow.json
│
├── streamlit/
│   ├── app3.py
│   └── requirements.txt
│
├── sql/
│   └── database.sql
│
├── docs/
│   └── documentacao.pdf
│
├── .env.example
├── .gitignore
└── README.md
```

> As credenciais e chaves de API não devem ser armazenadas no repositório.

---

## 🔐 Segurança e credenciais

As credenciais utilizadas pelo projeto devem permanecer fora do código versionado.

Exemplo de variáveis de ambiente:

```env
GEMINI_API_KEY=
DATABASE_URL=
```

O arquivo `.env` deve estar presente no `.gitignore`:

```gitignore
.env
.env.*
!.env.example
```

O arquivo `.env.example` pode ser disponibilizado no repositório contendo apenas os nomes das variáveis, sem valores reais.

---

## 🚨 Dados fictícios

Este projeto utiliza **dados e documentos fictícios para demonstração**.

Nenhuma informação financeira ou documento fiscal real deve ser utilizado em um ambiente público sem os controles adequados de segurança, privacidade e proteção de dados.

---

## 🚀 Roadmap

Possíveis evoluções para uma versão mais próxima de um ambiente produtivo:

### 🔐 IAM e controle de acesso

Implementação de autenticação integrada, como SSO, com permissões específicas de acordo com o perfil do usuário.

Exemplo:

```text
Gestor
 └── Visualizar + Aprovar

Financeiro
 └── Visualizar + Processar

Administrador
 └── Gestão completa
```

### 💾 Backup

Implementação de backups automatizados do PostgreSQL e estratégia de recuperação de dados.

### 🔔 Alertas

Envio automático de notificações por e-mail ou Microsoft Teams para notas que permaneçam pendentes de aprovação por determinado período.

### 📥 Múltiplas caixas de e-mail

Evolução do MVP para permitir que diferentes empresas ou unidades tenham suas próprias caixas de entrada.

---

## 📈 Benefícios Esperados

A solução busca gerar ganhos principalmente em:

**Redução de trabalho manual**

Menos tempo gasto baixando documentos, lendo informações e digitando dados.

**Padronização**

Documentos recebidos em PDF ou XML passam a alimentar uma estrutura de dados padronizada.

**Rastreabilidade**

As informações ficam armazenadas em banco de dados, permitindo acompanhar o histórico do processo.

**Redução de duplicidades**

O banco atua como uma camada adicional de proteção contra lançamentos repetidos.

**Visibilidade**

Gestores e equipe financeira conseguem acompanhar o processo através de um dashboard.

---

## 🧩 Conceitos aplicados

Este projeto demonstra a aplicação prática de conceitos de:

* Automação de processos;
* Engenharia de Dados;
* ETL/ELT;
* Integração de APIs e serviços;
* Processamento de documentos;
* Inteligência Artificial;
* Banco de dados relacional;
* Validação de dados;
* Controle de duplicidade;
* Dashboarding;
* Human-in-the-loop;
* Tratamento de exceções;
* Segurança de credenciais;
* Versionamento com Git.

---

## 👨‍💻 Sobre o projeto

Projeto desenvolvido como demonstração prática de automação de processos utilizando **n8n + IA + PostgreSQL + Streamlit**.

O foco está na construção de uma solução de ponta a ponta:

```text
Documento
    ↓
Ingestão
    ↓
Processamento
    ↓
Extração com IA
    ↓
Validação
    ↓
Banco de Dados
    ↓
Dashboard
    ↓
Decisão Humana
```

---

## ⚠️ Status do projeto

**MVP / Projeto de demonstração**

O projeto foi desenvolvido para demonstrar a arquitetura e o funcionamento de uma solução automatizada de processamento de notas fiscais.

Para utilização em produção, seriam necessários controles adicionais de segurança, autenticação, observabilidade, governança de dados e backup.
