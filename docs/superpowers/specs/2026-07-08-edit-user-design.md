# Edit User ("Wysig") Feature — Design

**Date:** 2026-07-08
**Status:** Approved

## Goal

Let an admin edit a user's profile from the admin user list. A "Wysig" button on each user card opens the existing create-user form pre-filled with that user's data. Saving sends the changes to the backend `PUT /gebruikers/{user_id}` endpoint, which updates the database.

## Approach

Reuse the existing `#createUserModal` in dual mode (create vs. edit) rather than duplicating a separate edit modal. A module-level `editingUserId` variable in `admin.js` tracks the mode: `null` means create, a user ID means edit.

## Components

### 1. "Wysig" button on user rows (`Webwerf/admin.js`, `addUserRow()`)

- Each user row rendered by `addUserRow()` gets a "Wysig" button in the `.admin-user-actions` area, styled consistently with existing action buttons.
- Clicking it calls `openEditUserModal(userId)`.

### 2. Edit mode for the create-user modal (`Webwerf/admin.html` + `admin.js`)

`openEditUserModal(userId)`:

- Fetches fresh user data via `GET /gebruikers/{user_id}`.
- Opens `#createUserModal` with fields pre-filled:
  - `new-user-name` ← `GEB_Naam`
  - `new-user-surname` ← `GEB_Van`
  - `new-user-email` ← `GEB_Epos`
  - `new-user-role` ← `Rol_ID`
  - `new-user-student-nr` ← `STU_Nommer` (visible only when the role is Student, same conditional logic as create)
- Password field (`new-user-password`) is left **empty and optional** in edit mode, with placeholder "Los leeg om wagwoord te behou". The `required` attribute is removed while editing and restored for create mode.
- Modal title changes to "Wysig Gebruiker"; submit button text changes to "Stoor Veranderinge".
- Sets `editingUserId = userId`.

### 3. Submit branching (`admin.js`, `submitNewUser()`)

- **Edit mode** (`editingUserId !== null`): builds a `UserUpdate` payload (`GEB_Naam`, `GEB_Van`, `GEB_Epos`, `Rol_ID`, `STU_Nommer` when applicable). `GEB_Wagwoord` is included only when the password field is non-blank. Calls `updateGebruiker(editingUserId, payload)`.
- **Create mode**: unchanged existing POST flow.
- On success (edit): close modal, reset the form back to create mode (title, button text, `required` on password, `editingUserId = null`), and refresh the edited user's row in the list (name, email, role badge) using the returned data.

### 4. API client method (`Webwerf/website_api_calls.js`)

New `updateGebruiker(userId, payload)` that sends `PUT /gebruikers/{userId}` via the existing `apiRequest()` helper (dynamic base URL + token injection).

## Backend

No backend changes required. Uses the existing updated endpoints:

- `GET /gebruikers/{user_id}` — fetch data to pre-fill the form.
- `PUT /gebruikers/{user_id}` (`opdateer_gebruiker()`, `main.py`) — accepts the optional-fields `UserUpdate` schema, hashes password only if provided, syncs sub-records (Student etc.), and validates e-pos/ID uniqueness excluding the current user.

## Error handling

- Backend validation errors (e.g. duplicate e-pos) are shown in the modal's existing error/message area, same as the create flow.
- If the `GET /gebruikers/{user_id}` fetch fails, show an error and do not open the modal.
- Closing/cancelling the modal always resets it back to create mode.

## Testing

Manual browser verification:

1. Click "Wysig" on a user → modal opens with correct pre-filled values, title "Wysig Gebruiker".
2. Change name/e-pos, leave password blank, save → row updates, database reflects change, password unchanged (login still works with old password).
3. Enter a new password on edit → password updated.
4. Change role to/from Student → student-number field toggles; sub-records sync on backend.
5. Duplicate e-pos → error shown in modal, modal stays open.
6. Cancel edit, then open "Skep Gebruiker" → form is empty and in create mode (password required again).
