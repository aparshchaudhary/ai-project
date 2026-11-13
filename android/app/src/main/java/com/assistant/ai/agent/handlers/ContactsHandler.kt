package com.assistant.ai.agent.handlers

import android.content.Context
import android.content.pm.PackageManager
import android.provider.ContactsContract
import androidx.core.content.ContextCompat
import com.assistant.ai.agent.models.ContactInfo

class ContactsHandler(private val context: Context) {

    fun searchContacts(query: String): List<ContactInfo> {
        val results = mutableListOf<ContactInfo>()
        if (ContextCompat.checkSelfPermission(
                context,
                android.Manifest.permission.READ_CONTACTS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return results
        }

        val cleanQuery = query.trim().lowercase()
        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone._ID,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER
        )

        val cursor = context.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            projection,
            null,
            null,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
        )

        cursor?.use {
            val idIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone._ID)
            val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)

            while (it.moveToNext()) {
                val id = if (idIndex >= 0) it.getString(idIndex) else ""
                val name = if (nameIndex >= 0) it.getString(nameIndex) else ""
                val number = if (numberIndex >= 0) it.getString(numberIndex) else ""

                if (name.lowercase().contains(cleanQuery) || cleanQuery.contains(name.lowercase())) {
                    results.add(ContactInfo(id = id, name = name, phone = number))
                }
            }
        }

        return results
    }
}
