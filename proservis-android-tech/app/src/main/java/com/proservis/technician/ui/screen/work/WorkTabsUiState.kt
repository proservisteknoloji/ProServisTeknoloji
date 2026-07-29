package com.proservis.technician.ui.screen.work

import com.proservis.technician.domain.model.UserSession
import com.proservis.technician.domain.model.WorkItem

data class WorkTabsUiState(
    val loading: Boolean = true,
    val session: UserSession? = null,
    val companyName: String = "",
    val companyLogoDataUrl: String = "",
    val locationRequestNonce: Int = 0,
    val openPoolItems: List<WorkItem> = emptyList(),
    val myItems: List<WorkItem> = emptyList(),
    val actionBusyId: String? = null,
    val errorMessage: String? = null,
)
