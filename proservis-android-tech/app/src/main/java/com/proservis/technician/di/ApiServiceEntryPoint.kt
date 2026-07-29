package com.proservis.technician.di

import com.proservis.technician.data.api.ApiService
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@EntryPoint
@InstallIn(SingletonComponent::class)
interface ApiServiceEntryPoint {
    fun apiService(): ApiService
}
