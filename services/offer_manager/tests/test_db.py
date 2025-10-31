import pytest
from unittest.mock import patch, MagicMock
from src import db as db_mod


class TestDBConnection:
    """Tests para conexión a base de datos"""
    
    @patch('src.db.psycopg2.connect')
    def test_get_connection_success(self, mock_connect, monkeypatch):
        monkeypatch.setenv('DB_HOST', 'localhost')
        monkeypatch.setenv('DB_NAME', 'test_db')
        monkeypatch.setenv('DB_USER', 'test_user')
        monkeypatch.setenv('DB_PASSWORD', 'test_pass')
        
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        conn = db_mod.get_connection()
        assert conn is not None
        mock_connect.assert_called_once()
    
    @patch('src.db.psycopg2.connect')
    def test_get_connection_error(self, mock_connect, monkeypatch):
        monkeypatch.setenv('DB_HOST', 'localhost')
        monkeypatch.setenv('DB_NAME', 'test_db')
        monkeypatch.setenv('DB_USER', 'test_user')
        monkeypatch.setenv('DB_PASSWORD', 'test_pass')
        
        mock_connect.side_effect = Exception('Connection failed')
        
        conn = db_mod.get_connection()
        assert conn is None


class TestExecuteQuery:
    """Tests para execute_query"""
    
    @patch('src.db.get_connection')
    def test_execute_query_select(self, mock_get_conn):
        from psycopg2.extras import RealDictCursor
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchall.return_value = [{'id': 1}]
        mock_get_conn.return_value = mock_conn
        
        result = db_mod.execute_query("SELECT * FROM test", fetch_all=True)
        assert result == [{'id': 1}]
        mock_cursor.execute.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('src.db.get_connection')
    def test_execute_query_insert_returning(self, mock_get_conn):
        from psycopg2.extras import RealDictCursor
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchone.return_value = {'id': 123}
        mock_cursor.statusmessage = "INSERT 1"
        mock_get_conn.return_value = mock_conn
        
        result = db_mod.execute_query("INSERT INTO test RETURNING id", fetch_one=True)
        assert result == {'id': 123}
        mock_conn.commit.assert_called_once()
    
    @patch('src.db.get_connection')
    def test_execute_query_insert_no_returning(self, mock_get_conn):
        from psycopg2.extras import RealDictCursor
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.rowcount = 1
        mock_get_conn.return_value = mock_conn
        
        result = db_mod.execute_query("INSERT INTO test VALUES (1)")
        assert result == 1
        mock_conn.commit.assert_called_once()
    
    @patch('src.db.get_connection')
    def test_execute_query_error_rollback(self, mock_get_conn):
        from psycopg2.extras import RealDictCursor
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_conn.cursor.side_effect = Exception('DB Error')
        mock_get_conn.return_value = mock_conn
        
        result = db_mod.execute_query("INSERT INTO test")
        assert result is None


class TestSalesPlansQueries:
    """Tests para queries de sales_plans"""
    
    @patch('src.db.execute_query')
    def test_get_sales_plans_success(self, mock_exec):
        mock_exec.return_value = [
            {'plan_id': 1, 'region': 'Norte'},
            {'plan_id': 2, 'region': 'Centro'}
        ]
        res = db_mod.get_sales_plans()
        assert isinstance(res, list)
        assert len(res) == 2
        assert res[0]['plan_id'] == 1
    
    @patch('src.db.execute_query')
    def test_get_sales_plans_empty(self, mock_exec):
        mock_exec.return_value = []
        res = db_mod.get_sales_plans()
        assert res == []
    
    @patch('src.db.execute_query')
    def test_get_sales_plan_products_success(self, mock_exec):
        mock_exec.return_value = [
            {
                'plan_product_id': 1,
                'product_id': 100,
                'individual_goal': 50.0
            }
        ]
        res = db_mod.get_sales_plan_products(plan_id=5)
        assert len(res) == 1
        assert res[0]['product_id'] == 100
    
    @patch('src.db.execute_query')
    def test_get_sales_plan_products_empty(self, mock_exec):
        mock_exec.return_value = []
        res = db_mod.get_sales_plan_products(1)
        assert res == []
    
    @patch('src.db.execute_query')
    def test_get_sales_plan_by_id_found(self, mock_exec):
        mock_exec.return_value = {
            'plan_id': 10,
            'region': 'Sur',
            'quarter': 'Q2',
            'year': 2025
        }
        res = db_mod.get_sales_plan_by_id(10)
        assert res is not None
        assert res['plan_id'] == 10
    
    @patch('src.db.execute_query')
    def test_get_sales_plan_by_id_not_found(self, mock_exec):
        mock_exec.return_value = None
        res = db_mod.get_sales_plan_by_id(999)
        assert res is None
    
    @patch('src.db.products_client')
    @patch('src.db.execute_query')
    def test_get_sales_plan_products_with_enrichment(self, mock_exec, mock_client):
        mock_exec.return_value = [
            {
                'plan_product_id': 1,
                'product_id': 100,
                'individual_goal': 50.0
            }
        ]
        mock_client.get_all_active_products.return_value = [
            {
                'product_id': 100,
                'sku': 'SKU-100',
                'name': 'Product 100',
                'value': 25.0,
                'unit_name': 'Caja',
                'unit_symbol': 'Cj'
            }
        ]
        res = db_mod.get_sales_plan_products(plan_id=5)
        assert len(res) == 1
        assert res[0]['sku'] == 'SKU-100'
        assert res[0]['product_name'] == 'Product 100'


class TestCreateSalesPlan:
    """Tests para crear sales plan"""
    
    @patch('src.db.execute_query')
    def test_create_sales_plan_success(self, mock_exec):
        mock_exec.side_effect = [
            {'plan_id': 50},  # INSERT plan
            None,             # INSERT product 1
            None              # INSERT product 2
        ]
        
        plan_data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': 100,
            'created_by': 1,
            'products': [
                {'product_id': 1, 'individual_goal': 60},
                {'product_id': 2, 'individual_goal': 40}
            ]
        }
        
        plan_id = db_mod.create_sales_plan(plan_data)
        assert plan_id == 50
        assert mock_exec.call_count == 3

