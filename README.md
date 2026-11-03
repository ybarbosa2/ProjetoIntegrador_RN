# Sistema de Gestão Operacional — R.N. Soluções Industriais

*Projeto Integrador "Fábrica de Software" — Engenharia de Software II (FATEC Ribeirão Preto)*

---

## Equipe de Desenvolvimento e Orientação

- **Integrantes da Equipe:**
  - Gabriela Rampazzo Galoni
  - Julia Palaretti
  - Marcos Misuki
  - Mariana Targas Barbosa
  - Yuri Barbosa
- **Docente Responsável:** Profa. Me. Eliza Bomfim

---

## Visão Geral do Problema e Módulos do MVP

A **R.N. Soluções Industriais**, atuante nos segmentos de metalurgia, caldeiraria e manutenção industrial, demandava a centralização e padronização de seus fluxos operacionais — anteriormente dispersos em controles manuais, planilhas isoladas e anotações físicas na oficina.

O MVP do **Sistema de Gestão Operacional** foi projetado e construído com foco nos três pilares críticos da operação diária:

1. **Módulo de Clientes (`US01` / `RF01` / `RN01`):**
   - Cadastro completo de pessoas jurídicas e físicas com geração automática de código sequencial (`CLI-XXXX`), validação fiscal centralizada (`CnpjValidator`), bloqueio de duplicidade de CPF/CNPJ, filtros por situação/busca e histórico integrado de Ordens de Serviço por cliente.
   - Inclui endpoint e modal de **Cadastro Rápido de Cliente** diretamente na tela de abertura de O.S. (`UC01-A1`).
2. **Módulo de Controle de Estoque (`US02` / `RF02` / `RN02`):**
   - Gestão de chapas, tubos, perfis, barras e consumíveis (`MAT-XXXX`), indicadores executivos (KPIs), classificação visual automática (`Normal`, `Baixo` e `Indisponível`), recomendação de quantidade mínima para compra, histórico auditável de entradas/saídas e **bloqueio rigoroso de saldo negativo** (`RN02`).
3. **Módulo de Ordens de Serviço e Orçamentos (`US03` / `US04` / `RF03`–`RF05` / `RN03`):**
   - Abertura e acompanhamento de Ordens de Serviço (`OS-XXXX`) com vínculo obrigatório a cliente (`RN03`), vínculo de materiais do estoque com baixa automática de saldo e geração instantânea do **Orçamento Comercial Padronizado** (`ORC-XXXX`) pronto para impressão/PDF via `CalculadoraOrcamentoService`.
4. **Governança DevOps e Feature Flags (`/configuracoes`):**
   - Painel administrativo de parâmetros da unidade ativa, rastreabilidade de registros e gerenciamento de *Feature Flags* (como `ENABLE_FISCAL_MODULE = False` para isolamento seguro do módulo experimental de Notas Fiscais).

---

## Arquitetura em Camadas

O sistema adota **Arquitetura em Camadas** em Python (`Flask` + `Flask-SQLAlchemy` + `SQLite` + `Jinja2` + `Tailwind CSS`), garantindo baixo acoplamento, alta coesão e testabilidade isolada:

```text
app/
├── __init__.py                         # Application Factory, filtros Jinja2 e Feature Flags
├── database.py                         # Instância do ORM SQLAlchemy
├── seed.py                             # Carga inicial fiel ao protótipo validado no Figma
├── models/                             # Entidades de domínio e propriedades de negócio
│   ├── cliente.py
│   ├── material.py
│   └── ordem_servico.py
├── repositories/                       # Persistência e consultas encapsuladas (Data Access)
│   ├── cliente_repository.py
│   ├── estoque_repository.py
│   └── os_repository.py
├── validators/                         # Regras de validação e normalização fiscal
│   └── cnpj_validator.py
├── services/                           # Orquestração de casos de uso e regras de negócio
│   ├── cliente_service.py
│   ├── estoque_service.py
│   ├── os_service.py
│   └── calculadora_orcamento_service.py
├── routes/                             # Controladores HTTP (Blueprints Flask)
│   ├── main_routes.py
│   ├── cliente_routes.py
│   ├── estoque_routes.py
│   └── os_routes.py
└── templates/                          # Interfaces Jinja2 fiéis ao Figma
    ├── base.html
    ├── home.html
    ├── configuracoes.html
    ├── clientes/
    ├── estoque/
    └── os/
```

---

## Como Executar o Projeto Localmente

### Pré-requisitos
- Python 3.11 ou superior
- Git

### Passo a passo

1. **Clone o repositório e acesse a pasta do projeto:**
   ```bash
   git clone <url-do-repositorio>
   cd ProjetoIntegrador_RN
   ```

2. **Crie e ative o ambiente virtual (`venv`):**
   - No Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - No Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie o servidor de desenvolvimento:**
   ```bash
   python run.py
   ```
   O banco SQLite será inicializado automaticamente com os dados de demonstração do protótipo e a aplicação estará disponível em `http://127.0.0.1:5000`.

---

## Testes Automatizados e Cobertura de Código

A qualidade do projeto é assegurada por testes unitários (incluindo TDD e isolamento com `MagicMock`) e testes de integração HTTP com `pytest` e `pytest-cov`, integrados ao pipeline de CI no GitHub Actions (`.github/workflows/ci.yml`).

- **Executar toda a suíte de testes:**
  ```bash
  pytest -v
  ```

- **Gerar relatório completo de cobertura de código no terminal:**
  ```bash
  pytest --cov=app --cov-report=term-missing
  ```
