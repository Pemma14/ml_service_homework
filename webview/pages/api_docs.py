import streamlit as st

def render_api_docs(api_url):
    st.markdown("### REST API примеры")

    st.markdown("""
    Вы можете использовать REST API напрямую для интеграции с другими системами.
    Ниже приведены примеры запросов с использованием `curl`.
    """)

    api_examples = st.tabs(["Авторизация", "Баланс", "ML-запросы", "История"])

    with api_examples[0]:
        st.markdown("#### Регистрация")
        st.code(f"""
curl -X POST {api_url}/api/v1/users/register \\
  -H "Content-Type: application/json" \\
  -d '{{
    "email": "user@example.com",
    "password": "password",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+79990000000"
  }}'
        """, language="bash")

        st.markdown("#### Вход")
        st.code(f"""
curl -X POST {api_url}/api/v1/users/login \\
  -H "Content-Type: application/json" \\
  -d '{{
    "email": "user@example.com",
    "password": "password"
  }}'
        """, language="bash")

    with api_examples[1]:
        st.markdown("#### Проверка баланса")
        st.code(f"""
curl -X GET {api_url}/api/v1/balance/check_balance \\
  -H "Authorization: Bearer YOUR_TOKEN"
        """, language="bash")

        st.markdown("#### Пополнение баланса")
        st.code(f"""
curl -X POST {api_url}/api/v1/balance/replenish \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"amount": 100}}'
        """, language="bash")

    with api_examples[2]:
        st.markdown("#### Асинхронный запрос")
        st.code(f"""
curl -X POST {api_url}/api/v1/requests/send_task \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "data": [{{
      "Возраст": 35.5,
      "ВНН/ПП": 1,
      "Клозапин": 0,
      "CYP2C19 1/2": 0,
      "CYP2C19 1/17": 1,
      "CYP2C19 *17/*17": 0,
      "CYP2D6 1/3": 0
    }}]
  }}'
        """, language="bash")

    with api_examples[3]:
        st.markdown("#### История запросов")
        st.code(f"""
curl -X GET {api_url}/api/v1/requests/history \\
  -H "Authorization: Bearer YOUR_TOKEN"
        """, language="bash")
