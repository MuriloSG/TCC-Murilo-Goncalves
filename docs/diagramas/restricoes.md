# Restrições do DER físico

Gerado por `make er-diagram` (comando `export_er_diagram`). Não edite à mão.

Constraints e índices que o diagrama não representa, com o SQL que o Django executa no PostgreSQL.

| Tabela | Nome | SQL |
|---|---|---|
| `accounts_permission` | `permission_code_format` | `ALTER TABLE "accounts_permission" ADD CONSTRAINT "permission_code_format" CHECK ("code"::text ~ E'^[A-Z]+(_[A-Z]+)*\\.[A-Z]+(_[A-Z]+)*$')` |
| `accounts_role` | `role_code_format` | `ALTER TABLE "accounts_role" ADD CONSTRAINT "role_code_format" CHECK ("code"::text ~ '^[A-Z]+(_[A-Z]+)*$')` |
| `accounts_role` | `role_name_unique_ci` | `CREATE UNIQUE INDEX "role_name_unique_ci" ON "accounts_role" ((LOWER("name")))` |
| `accounts_rolepermission` | `role_permission_unique` | `ALTER TABLE "accounts_rolepermission" ADD CONSTRAINT "role_permission_unique" UNIQUE ("role_id", "permission_id")` |
| `accounts_user` | `user_email_unique_ci` | `CREATE UNIQUE INDEX "user_email_unique_ci" ON "accounts_user" ((LOWER("email")))` |
| `accounts_user` | `user_username_unique_ci` | `CREATE UNIQUE INDEX "user_username_unique_ci" ON "accounts_user" ((LOWER("username")))` |
| `accounts_userrole` | `user_role_unique` | `ALTER TABLE "accounts_userrole" ADD CONSTRAINT "user_role_unique" UNIQUE ("user_id", "role_id")` |
| `accounts_userrole` | `user_role_one_per_user` | `ALTER TABLE "accounts_userrole" ADD CONSTRAINT "user_role_one_per_user" UNIQUE ("user_id")` |
| `audit_auditlog` | `audit_log_created_idx` | `CREATE INDEX "audit_log_created_idx" ON "audit_auditlog" ("created_at" DESC)` |
| `audit_auditlog` | `audit_log_user_idx` | `CREATE INDEX "audit_log_user_idx" ON "audit_auditlog" ("user_id", "created_at" DESC)` |
| `audit_auditlog` | `audit_log_action_idx` | `CREATE INDEX "audit_log_action_idx" ON "audit_auditlog" ("action", "created_at" DESC)` |
| `audit_auditlog` | `audit_log_resource_idx` | `CREATE INDEX "audit_log_resource_idx" ON "audit_auditlog" ("resource", "resource_id")` |
| `bookings_booking` | `booking_range_valid` | `ALTER TABLE "bookings_booking" ADD CONSTRAINT "booking_range_valid" CHECK ("starts_at" < ("ends_at"))` |
| `bookings_booking` | `booking_no_overlap` | `ALTER TABLE "bookings_booking" ADD CONSTRAINT "booking_no_overlap" EXCLUDE USING GIST ("space_id" WITH =, (TSTZRANGE("starts_at", "ends_at", '[)')) WITH &&)` |
| `bookings_bookingrequest` | `booking_request_range_valid` | `ALTER TABLE "bookings_bookingrequest" ADD CONSTRAINT "booking_request_range_valid" CHECK ("start_time" < ("end_time"))` |
| `bookings_bookingrequest` | `booking_request_suggestion_range_valid` | `ALTER TABLE "bookings_bookingrequest" ADD CONSTRAINT "booking_request_suggestion_range_valid" CHECK ((("suggested_end_time" IS NULL AND "suggested_start_time" IS NULL) OR "suggested_start_time" < ("suggested_end_time")))` |
| `bookings_bookingrequest` | `booking_request_owner_idx` | `CREATE INDEX "booking_request_owner_idx" ON "bookings_bookingrequest" ("requested_by_id", "created_at" DESC)` |
| `bookings_bookingrequest` | `booking_request_status_idx` | `CREATE INDEX "booking_request_status_idx" ON "bookings_bookingrequest" ("status", "date")` |
| `imports_import` | `import_operation_matches_status` | `ALTER TABLE "imports_import" ADD CONSTRAINT "import_operation_matches_status" CHECK ((("operation" IS NULL AND NOT ("status" = 'RECEBIDA')) OR ("operation" = 'PREVIA' AND "operation" IS NOT NULL AND "status" = 'RECEBIDA') OR ("operation" = 'ATUALIZACAO' AND "operation" IS NOT NULL AND "status" IN ('VALIDADA', 'PENDENTE')) OR ("operation" = 'CONFIRMACAO' AND "operation" IS NOT NULL AND "status" = 'VALIDADA')))` |
| `imports_import` | `import_kind_created_idx` | `CREATE INDEX "import_kind_created_idx" ON "imports_import" ("kind", "created_at" DESC)` |
| `imports_import` | `import_pending_operation_idx` | `CREATE INDEX "import_pending_operation_idx" ON "imports_import" ("next_attempt_at") WHERE "operation" IS NOT NULL` |
| `imports_importrow` | `import_row_line_unique` | `ALTER TABLE "imports_importrow" ADD CONSTRAINT "import_row_line_unique" UNIQUE ("parent_id", "line_number")` |
| `notices_notification` | `notification_recipient_read` | `CREATE INDEX "notification_recipient_read" ON "notices_notification" ("recipient_id", "read_at")` |
| `outbox_outboxentry` | `outbox_entry_pending_unique` | `CREATE UNIQUE INDEX "outbox_entry_pending_unique" ON "outbox_outboxentry" ("kind", "reference") WHERE "status" = 'A_ENVIAR'` |
| `outbox_outboxentry` | `outbox_entry_due_idx` | `CREATE INDEX "outbox_entry_due_idx" ON "outbox_outboxentry" ("status", "next_attempt_at")` |
| `schedule_allocation` | `allocation_unique` | `ALTER TABLE "schedule_allocation" ADD CONSTRAINT "allocation_unique" UNIQUE NULLS NOT DISTINCT ("semester_id", "class_group_id", "weekday", "time_slot_id", "subject_id", "valid_from")` |
| `schedule_allocation` | `allocation_space_idx` | `CREATE INDEX "allocation_space_idx" ON "schedule_allocation" ("semester_id", "space_id", "weekday")` |
| `schedule_allocation` | `allocation_slot_idx` | `CREATE INDEX "allocation_slot_idx" ON "schedule_allocation" ("semester_id", "weekday", "time_slot_id")` |
| `schedule_allocation` | `allocation_group_idx` | `CREATE INDEX "allocation_group_idx" ON "schedule_allocation" ("semester_id", "class_group_id")` |
| `schedule_allocationexception` | `allocation_exception_unique` | `ALTER TABLE "schedule_allocationexception" ADD CONSTRAINT "allocation_exception_unique" UNIQUE ("allocation_id", "date")` |
| `schedule_classgroup` | `class_group_label_unique_ci` | `CREATE UNIQUE INDEX "class_group_label_unique_ci" ON "schedule_classgroup" ("course_id", (LOWER("label")))` |
| `schedule_classoffering` | `class_offering_unique` | `ALTER TABLE "schedule_classoffering" ADD CONSTRAINT "class_offering_unique" UNIQUE ("semester_id", "subject_id", "class_group_id")` |
| `schedule_classoffering` | `class_offering_group_idx` | `CREATE INDEX "class_offering_group_idx" ON "schedule_classoffering" ("semester_id", "class_group_id")` |
| `schedule_course` | `course_name_unique_ci` | `CREATE UNIQUE INDEX "course_name_unique_ci" ON "schedule_course" ((LOWER("name")))` |
| `schedule_semester` | `semester_period_valid` | `ALTER TABLE "schedule_semester" ADD CONSTRAINT "semester_period_valid" CHECK ((("end_date" IS NULL AND "start_date" IS NULL) OR ("end_date" IS NOT NULL AND "start_date" IS NOT NULL AND "start_date" <= ("end_date"))))` |
| `schedule_space` | `space_name_unique_ci` | `CREATE UNIQUE INDEX "space_name_unique_ci" ON "schedule_space" ((LOWER("name")))` |
| `schedule_spacedecision` | `space_decision_unique_ci` | `CREATE UNIQUE INDEX "space_decision_unique_ci" ON "schedule_spacedecision" ("importation_id", (LOWER("found_name")))` |
| `schedule_spacename` | `space_alias_unique_ci` | `CREATE UNIQUE INDEX "space_alias_unique_ci" ON "schedule_spacename" ((LOWER("name")))` |
| `schedule_subject` | `subject_name_unique_ci` | `CREATE UNIQUE INDEX "subject_name_unique_ci" ON "schedule_subject" ((LOWER("name")))` |
| `schedule_teacher` | `teacher_name_unique_ci` | `CREATE UNIQUE INDEX "teacher_name_unique_ci" ON "schedule_teacher" ((LOWER("name")))` |
| `schedule_teachingassignment` | `teaching_assignment_unique` | `ALTER TABLE "schedule_teachingassignment" ADD CONSTRAINT "teaching_assignment_unique" UNIQUE ("offering_id", "teacher_id")` |
| `schedule_teachingassignment` | `assignment_teacher_idx` | `CREATE INDEX "assignment_teacher_idx" ON "schedule_teachingassignment" ("teacher_id", "offering_id")` |
| `schedule_timeslot` | `time_slot_unique` | `ALTER TABLE "schedule_timeslot" ADD CONSTRAINT "time_slot_unique" UNIQUE ("semester_id", "start_time", "end_time")` |
| `schedule_timeslot` | `time_slot_start_before_end` | `ALTER TABLE "schedule_timeslot" ADD CONSTRAINT "time_slot_start_before_end" CHECK ("start_time" < ("end_time"))` |
