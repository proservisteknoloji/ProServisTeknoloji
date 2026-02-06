#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure SQL Reset ve Test Kullanıcıları Oluşturma Helper
"""
import logging
import bcrypt

def reset_azure_and_create_test_users(azure_manager):
    """
    Azure'ı temizle ve test kullanıcıları oluştur
    
    Args:
        azure_manager: AzureSQLManager instance
        
    Returns:
        bool: Başarılı ise True
    """
    # Azure entegrasyonu askıya alındı
    pass


def _clean_azure(azure_manager):
    """Azure'daki tüm company schema'larını ve kullanıcıları sil"""
    # Azure entegrasyonu askıya alındı
    return False


def _create_test_users(azure_manager):
    """Test kullanıcıları oluştur ve schema'larını hazırla"""
    users = [
        {
            'username': 'test1',
            'password': '123456',
            'full_name': 'Test User 1',
            'company_name': 'Test Company 1',
            'role': 'Admin'
        },
        {
            'username': 'test2',
            'password': '123456',
            'full_name': 'Test User 2',
            'company_name': 'Test Company 2',
            'role': 'Admin'
        }
    ]
    
    for user_data in users:
        try:
            logging.info(f"  👤 {user_data['username']} oluşturuluyor...")
            
            # Şifre hash'i
            password_hash = bcrypt.hashpw(
                user_data['password'].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Kullanıcı kaydet
            result = azure_manager.register_user(
                username=user_data['username'],
                password_hash=password_hash,
                full_name=user_data['full_name'],
                role=user_data['role'],
                company_name=user_data['company_name']
            )
            
            if not result['success']:
                logging.error(f"    ❌ Kullanıcı oluşturulamadı: {result['error']}")
                continue
            
            logging.info(f"    ✅ Kullanıcı oluşturuldu (ID: {result['user_id']})")
            
            # register_user'dan dönen company_schema'yı kullan
            company_schema = result['company_schema']
            logging.info(f"    ✅ Schema: {company_schema}")
            
            # Company schema oluştur
            logging.info(f"    🏢 Schema oluşturuluyor...")
            if not azure_manager.ensure_company_schema(user_data['company_name']):
                logging.warning(f"    ⚠️ Schema oluşturulamadı")
                continue
            
            # Tabloları oluştur
            logging.info(f"    📋 Tablolar oluşturuluyor...")
            if azure_manager.create_tables_from_sqlite_schema(company_schema):
                logging.info(f"    ✅ Tablolar oluşturuldu")
            else:
                logging.warning(f"    ⚠️ Tablolar oluşturulamadı")
            
            logging.info(f"  ✅ {user_data['username']} hazır!")
            
        except Exception as e:
            logging.error(f"  ❌ {user_data['username']} oluşturulurken hata: {e}")
            continue
    
    logging.info("✅ Test kullanıcıları oluşturuldu")
    return True
