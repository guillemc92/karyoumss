# Inventario de pruebas unitarias

**BIOMED UMSS — Plataforma de Cariotipado Asistido por IA**

| | |
|---|---|
| Nombre del equipo | **BIOMED UMSS** |
| Modalidad | Individual (G04) |
| Integrante | Ing. Guillermo Mamani Chambi |
| Repositorio | `karyoumss` — rama `feature/clinic-django-stack` |
| Fecha de ejecucion | 4 de septiembre de 2026 |
| **Total de unit tests** | **1616** |
| Resultado | **1616/1616 en verde** (0 fallos) |

> Los nombres de este documento no se transcribieron a mano: se generaron
> desde la salida real de `pytest --collect-only` y del reporter JSON de
> `vitest`, ejecutados el mismo dia sobre la rama indicada.

## 1 · Resumen por modulo

| Modulo | Runner | Ficheros | Unit tests | Alcance |
|---|---|---:|---:|---|
| `backend-clinic` | pytest | 34 | **627** | Django · bounded context clinico |
| `backend-admin` | pytest | 21 | **345** | Django · autoridad JWT, usuarios y configuracion |
| `backend-ml` | pytest | 5 | **44** | FastAPI · motor de inferencia |
| `frontend-clinic` | vitest | 49 | **380** | React + Konva · visor y correccion de cariotipo |
| `frontend-admin` | vitest | 21 | **220** | React · panel de administracion |
| **TOTAL** | | | **1616** | |

### Como reproducirlo

```bash
cd backend-clinic  && .venv/Scripts/python -m pytest          # 627
cd backend-admin   && .venv/Scripts/python -m pytest          # 345
cd backend-ml      && python -m pytest                        # 44
cd frontend-clinic && npm test                                # 380
cd frontend-admin  && npm test                                # 220
```

---

## 2 · `backend-clinic` — 627 unit tests

### `apps/samples/tests/test_agente_guardrails.py`

**TestFreno** — 4 pruebas

- `test_un_modelo_que_nunca_para_se_corta_en_MAX_PASOS`
- `test_el_corte_queda_en_la_traza_y_no_se_disfraza_de_respuesta`
- `test_el_tope_se_puede_bajar_pero_no_ignorar`
- `test_si_responde_texto_corta_antes_del_tope`

**TestDecisionesReproducibles** — 1 prueba

- `test_temperatura_cero_en_TODAS_las_llamadas`

**TestCinturon** — 8 pruebas

- `test_con_confirmado_true_NO_ejecuta`
- `test_la_negativa_llega_ANTES_de_mirar_los_datos`
- `test_sin_confirmar_devuelve_un_PLAN_y_tampoco_ejecuta`
- `test_el_estado_del_caso_NO_cambia_ni_confirmando`
- `test_un_caso_inexistente_se_dice_no_se_inventa`
- `test_el_guardrail_viaja_en_la_DESCRIPCION_que_lee_el_modelo`
- `test_ejecutar_normaliza_argumentos_ausentes`
- `test_el_nombre_publicado_es_el_que_espera_el_catalogo`

**TestCajaNegra** — 6 pruebas

- `test_registra_pregunta_accion_observacion_y_respuesta`
- `test_la_observacion_lleva_lo_que_devolvio_la_herramienta`
- `test_suma_los_tokens_para_poder_ver_el_coste`
- `test_una_herramienta_que_revienta_NO_tumba_al_agente`
- `test_argumentos_json_invalidos_no_rompen_el_bucle`
- `test_la_traza_es_serializable_para_devolverla_por_la_API`

**TestDegradacion** — 2 pruebas

- `test_con_la_IA_apagada_lanza_AgenteError`
- `test_si_el_modelo_falla_se_convierte_en_AgenteError_con_traza`

**TestElPlanDiceQueBloquea** — 3 pruebas

- `test_avisa_si_el_caso_no_esta_en_READY`
- `test_cuenta_los_naranjas_sin_resolver_y_cita_RN_02`
- `test_un_caso_limpio_dice_que_puede_validarse`

### `apps/samples/tests/test_cadena_orden_instante.py`

**(funciones sueltas)** — 13 pruebas

- `test_eventos_seguidos_no_rompen_la_cadena[0]`
- `test_eventos_seguidos_no_rompen_la_cadena[1]`
- `test_eventos_seguidos_no_rompen_la_cadena[2]`
- `test_eventos_seguidos_no_rompen_la_cadena[3]`
- `test_eventos_seguidos_no_rompen_la_cadena[4]`
- `test_eventos_seguidos_no_rompen_la_cadena[5]`
- `test_eventos_seguidos_no_rompen_la_cadena[6]`
- `test_eventos_seguidos_no_rompen_la_cadena[7]`
- `test_eventos_seguidos_no_rompen_la_cadena[8]`
- `test_eventos_seguidos_no_rompen_la_cadena[9]`
- `test_los_instantes_son_estrictamente_crecientes`
- `test_el_orden_de_verificacion_es_el_de_escritura`
- `test_cada_evento_apunta_al_anterior`

### `apps/samples/tests/test_detail_view.py`

**TestGet** — 6 pruebas

- `test_analista_ve_propia`
- `test_analista_no_ve_ajena_403`
- `test_supervisor_ve_cualquiera`
- `test_admin_ve_cualquiera`
- `test_no_existe_404`
- `test_anonimo_401`

**TestPatch** — 5 pruebas

- `test_analista_edita_propia`
- `test_analista_no_edita_ajena_403`
- `test_supervisor_edita_cualquiera`
- `test_rechaza_status_field_not_allowed`
- `test_rechaza_chn_code_field_not_allowed`

**TestDelete** — 6 pruebas

- `test_admin_elimina`
- `test_analista_no_puede_eliminar_403`
- `test_supervisor_no_puede_eliminar_403`
- `test_no_elimina_validated_409`
- `test_anonimo_401`
- `test_eliminada_no_aparece_en_get_posterior`

### `apps/samples/tests/test_fields.py`

**TestEncryptedTextField** — 4 pruebas

- `test_roundtrip_encrypts_and_decrypts`
- `test_stored_value_is_not_plaintext`
- `test_empty_string_is_not_encrypted`
- `test_multiple_encrypted_fields_roundtrip`

### `apps/samples/tests/test_imagen_metafase.py`

**(funciones sueltas)** — 18 pruebas

- `test_registrar_con_un_recorte_falla_y_no_crea_la_muestra`
- `test_detecta_el_recorte_aunque_no_sea_el_primero`
- `test_un_borrador_no_se_valida_porque_no_se_analiza`
- `test_el_mensaje_orienta_en_vez_de_solo_negar`
- `test_lee_las_dimensiones_de_cada_formato[bmp]`
- `test_lee_las_dimensiones_de_cada_formato[png]`
- `test_lee_las_dimensiones_de_cada_formato[jpeg]`
- `test_bmp_de_arriba_abajo_tiene_alto_negativo_y_se_normaliza`
- `test_formato_desconocido_devuelve_none`
- `test_lo_que_no_se_puede_medir_se_deja_pasar`
- `test_los_recortes_del_caso_real_se_rechazan[60-119]`
- `test_los_recortes_del_caso_real_se_rechazan[183-248]`
- `test_los_recortes_del_caso_real_se_rechazan[405-305]`
- `test_las_metafases_reales_del_dataset_pasan[1024-768]`
- `test_las_metafases_reales_del_dataset_pasan[1024-1177]`
- `test_las_metafases_reales_del_dataset_pasan[1280-1290]`
- `test_el_limite_exacto_se_acepta`
- `test_un_pixel_por_debajo_se_rechaza`

### `apps/samples/tests/test_iscn_service.py`

**TestGeneracion** — 5 pruebas

- `test_cariotipo_normal`
- `test_trisomia_21_detectada_del_conteo_real`
- `test_femenino`
- `test_ignora_los_cromosomas_desactivados`
- `test_la_generacion_normal_no_emite_evento`

**TestGateDeEstado** — 6 pruebas

- `test_rechaza_si_no_esta_firmado[PENDING_AI]`
- `test_rechaza_si_no_esta_firmado[READY]`
- `test_rechaza_si_no_esta_firmado[IN_ANALYSIS]`
- `test_rechaza_si_no_esta_firmado[ANALYST_VALIDATED]`
- `test_rechaza_si_no_esta_firmado[REPORTED]`
- `test_caso_sin_cromosomas_no_inventa_un_iscn`

**TestInmutabilidadRN04** — 2 pruebas

- `test_regenerar_sin_override_es_rechazado`
- `test_el_iscn_no_cambia_tras_un_intento_fallido`

**TestOverride** — 5 pruebas

- `test_impone_el_string_del_supervisor`
- `test_deja_traza_con_el_original_y_la_justificacion`
- `test_exige_justificacion`
- `test_rechaza_gramatica_invalida`
- `test_permite_corregir_un_iscn_ya_generado`

**TestModoDegradado** — 1 prueba

- `test_propaga_el_modo_al_evento`

**TestEndpoint** — 7 pruebas

- `test_genera_y_devuelve_el_iscn`
- `test_no_reportable_da_409`
- `test_regenerar_da_409`
- `test_override_invalido_da_400`
- `test_no_hay_patch`
- `test_el_analista_no_puede_reportar`
- `test_anonimo_rechazado`

### `apps/samples/tests/test_karyotype.py`

**TestChromosomeSemaphore** — 6 pruebas

- `test_green_above_threshold`
- `test_green_exactly_at_threshold`
- `test_orange_below_threshold`
- `test_orange_just_below_threshold`
- `test_red_when_confidence_null`
- `test_str_representations`

**TestKaryotypeSerializer** — 4 pruebas

- `test_summary_counts`
- `test_resolved_orange_not_counted_as_unresolved`
- `test_not_blocked_when_all_green`
- `test_serializer_exposes_semaphore_and_sample_id`

**TestKaryotypeView** — 6 pruebas

- `test_analista_ve_propio_200`
- `test_sin_cariotipo_404`
- `test_analista_no_ve_ajena_403`
- `test_supervisor_ve_cualquiera_200`
- `test_anonimo_401`
- `test_muestra_inexistente_404`

**TestSeedKaryotype** — 2 pruebas

- `test_seed_creates_46_chromosomes_with_3_oranges`
- `test_seed_is_idempotent`

### `apps/samples/tests/test_karyotype_p2.py`

**TestAuditTrail** — 5 pruebas

- `test_hash_chain_links_events`
- `test_verify_chain_true_when_intact`
- `test_verify_chain_false_when_tampered_in_db`
- `test_append_only_blocks_update`
- `test_chain_is_per_sample`

**TestKaryotypeP2Services** — 8 pruebas

- `test_view_xai_sets_flag_and_emits`
- `test_resolve_requires_xai`
- `test_resolve_after_xai_succeeds`
- `test_resolve_non_orange_rejected`
- `test_mark_anomaly`
- `test_validate_blocked_with_pending_orange`
- `test_validate_succeeds_when_all_resolved`
- `test_validate_without_karyotype_blocked`

**TestKaryotypeP2Endpoints** — 12 pruebas

- `test_xai_declara_si_hay_explicacion_o_por_que_no`
- `test_xai_marca_el_cromosoma_aunque_no_haya_mapa`
- `test_resolve_without_xai_returns_409`
- `test_resolve_after_xai_returns_200`
- `test_resolve_green_returns_400`
- `test_anomaly_endpoint`
- `test_validate_blocked_returns_409`
- `test_validate_success`
- `test_audit_endpoint_lists_events`
- `test_chromosome_not_found_404`
- `test_analista_no_ajena_403`
- `test_anonimo_401`

### `apps/samples/tests/test_karyotype_p3.py`

**TestReclassify** — 4 pruebas

- `test_reclassify_changes_class_and_resolves`
- `test_reclassify_invalid_class_rejected`
- `test_reclassify_same_class_rejected`
- `test_reclassify_unblocks_case`

**TestSplit** — 2 pruebas

- `test_split_creates_second_chromosome`
- `test_split_new_index_is_next`

**TestJoin** — 3 pruebas

- `test_join_absorbs_and_unions_bbox`
- `test_join_self_rejected`
- `test_joined_chromosome_excluded_from_summary`

**TestCross** — 1 prueba

- `test_resolve_cross_marks_resolved`

**TestCaseLock** — 2 pruebas

- `test_edits_blocked_after_validation`
- `test_audit_chain_intact_after_p3_ops`

**TestP3Endpoints** — 11 pruebas

- `test_reclassify_endpoint`
- `test_reclassify_invalid_400`
- `test_reclassify_same_400`
- `test_split_endpoint_201`
- `test_join_endpoint`
- `test_join_self_400`
- `test_join_other_not_found_404`
- `test_cross_endpoint`
- `test_case_locked_409`
- `test_analista_ajena_403`
- `test_anonimo_401`

### `apps/samples/tests/test_karyotype_p4.py`

**TestDegradedMode** — 6 pruebas

- `test_service_records_mode_degradado`
- `test_service_defaults_to_auto`
- `test_header_marks_event_degradado`
- `test_no_header_defaults_auto`
- `test_mode_is_part_of_hash_chain`
- `test_mode_exposed_in_serializer`

**TestPipelineHealth** — 3 pruebas

- `test_health_available_when_circuit_closed`
- `test_health_degraded_when_circuit_open`
- `test_health_requires_auth`

### `apps/samples/tests/test_ml_ingest.py`

**TestIngest** — 4 pruebas

- `test_creates_karyotype_and_chromosomes`
- `test_resolution_status_derived_from_confidence`
- `test_position_index_per_class`
- `test_ingest_replaces_existing`

**TestRegistrationFlow** — 3 pruebas

- `test_register_segments_and_ingests`
- `test_register_degraded_persists_without_karyotype`
- `test_draft_does_not_process`

**TestReprocess** — 2 pruebas

- `test_reprocess_reads_stored_image`
- `test_reprocess_without_image_degraded`

**TestProcessEndpoint** — 1 prueba

- `test_process_reprocesses_to_ready`

### `apps/samples/tests/test_narrative_service.py`

**TestGeneracionYPersistencia** — 5 pruebas

- `test_persiste_el_borrador_y_su_procedencia`
- `test_emite_evento_auditable_con_el_iscn_de_entrada`
- `test_el_evento_entra_en_la_cadena_de_hash`
- `test_pasa_el_conteo_de_cromosomas_activos`
- `test_regenerar_sobrescribe_el_borrador_y_deja_dos_eventos`

**TestDegradacionNoBloqueante** — 5 pruebas

- `test_servicio_caido_no_lanza`
- `test_alucinacion_descarta_el_borrador`
- `test_fallo_no_emite_evento_de_auditoria`
- `test_sin_iscn_no_llama_al_modelo`
- `test_caso_sin_cariotipo_no_revienta`

**TestModoDegradado** — 1 prueba

- `test_propaga_el_modo_al_evento`

**TestEndpointNarrativa** — 9 pruebas

- `test_devuelve_el_borrador`
- `test_marca_la_salida_como_borrador`
- `test_usa_el_iscn_persistido_del_caso`
- `test_sin_iscn_generado_no_narra`
- `test_el_llm_caido_devuelve_200_no_error`
- `test_el_analista_no_puede_generarla`
- `test_anonimo_rechazado`
- `test_devuelve_el_objeto_estructurado`
- `test_sin_narrativa_el_estructurado_es_nulo`

### `apps/samples/tests/test_permissions.py`

**TestRoleForUser** — 3 pruebas

- `test_analista`
- `test_supervisor`
- `test_admin`

**TestIsClinicRole** — 2 pruebas

- `test_authenticated_allowed`
- `test_anonymous_denied`

**TestIsAdminRole** — 3 pruebas

- `test_admin_allowed`
- `test_supervisor_denied`
- `test_analista_denied`

**TestIsOwnerOrStaff** — 3 pruebas

- `test_owner_allowed`
- `test_non_owner_denied`
- `test_supervisor_sees_any`

### `apps/samples/tests/test_process_status_view.py`

**TestProcess** — 8 pruebas

- `test_analista_procesa_propia`
- `test_analista_no_procesa_ajena_403`
- `test_supervisor_procesa_cualquiera`
- `test_ya_processing_409`
- `test_ml_degraded_503_sin_imagen`
- `test_no_existe_404`
- `test_anonimo_401`
- `test_reprocesa_desde_ready`

**TestStatus** — 5 pruebas

- `test_analista_ve_status_propia`
- `test_analista_no_ve_status_ajena_403`
- `test_status_ready_incluye_conteo`
- `test_no_existe_404`
- `test_anonimo_401`

### `apps/samples/tests/test_rbac_admin.py`

**TestTipoObjetoAdmin** — 1 prueba

- `test_objetos_count`

**TestObjetoAdmin** — 1 prueba

- `test_opciones_count`

**TestGrupoAdmin** — 2 pruebas

- `test_usuarios_count`
- `test_privilegios_count_solo_cuenta_permitidos`

**TestPrivilegioGrupoAdmin** — 2 pruebas

- `test_permitido_badge_si`
- `test_permitido_badge_no`

**TestPrivilegioIndividualAdmin** — 6 pruebas

- `test_permitido_display_sin_excepcion`
- `test_permitido_display_forzado_si`
- `test_permitido_display_forzado_no`
- `test_efecto_real_sin_excepcion_usa_grupo`
- `test_efecto_real_difiere_del_grupo_resalta_rojo`
- `test_efecto_real_coincide_con_grupo_resalta_azul`

### `apps/samples/tests/test_rbac_models.py`

**TestSeedJerarquia** — 4 pruebas

- `test_seed_crea_las_6_opciones_esperadas`
- `test_seed_crea_los_3_grupos_esperados`
- `test_seed_matriz_reproduce_adr0018`
- `test_seed_resto_de_opciones_permitidas_para_los_3_grupos`

**TestSeedUsuariosExistentes** — 2 pruebas

- `test_signal_asigna_analista_a_usuario_nuevo_sin_staff`
- `test_signal_no_reasigna_si_ya_tiene_grupo`

**TestConstraints** — 5 pruebas

- `test_unique_objeto_opcion_nombre`
- `test_unique_opcion_codigo`
- `test_unique_grupo_opcion`
- `test_unique_usuario_grupo`
- `test_unique_usuario_opcion_individual`

**TestStrRepresentations** — 7 pruebas

- `test_tipo_objeto_str`
- `test_objeto_str`
- `test_opcion_str`
- `test_grupo_str`
- `test_privilegio_grupo_str`
- `test_usuario_grupo_str`
- `test_privilegio_individual_str`

### `apps/samples/tests/test_recrop.py`

**TestReclasificacion** — 2 pruebas

- `test_el_recorte_arrastra_una_clase_nueva`
- `test_se_clasifica_con_el_bbox_NUEVO`

**TestVuelveALaCola** — 1 prueba

- `test_un_recorte_nuevo_reabre_la_revision`

**TestDegradacion** — 2 pruebas

- `test_sin_IA_se_guarda_el_recorte_igual`
- `test_la_traza_dice_que_NO_se_reclasifico`

**TestTraza** — 1 prueba

- `test_guarda_el_antes_y_el_despues`

**TestValidacion** — 5 pruebas

- `test_un_bbox_invalido_se_rechaza[bbox0]`
- `test_un_bbox_invalido_se_rechaza[bbox1]`
- `test_un_bbox_invalido_se_rechaza[bbox2]`
- `test_un_bbox_invalido_se_rechaza[bbox3]`
- `test_un_bbox_invalido_no_deja_evento`

### `apps/samples/tests/test_register_view.py`

**TestSampleRegisterView** — 10 pruebas

- `test_register_complete_returns_201`
- `test_register_draft_returns_201`
- `test_register_unauthenticated_returns_401`
- `test_register_invalid_chn_format_returns_400`
- `test_register_missing_patient_name_returns_400`
- `test_register_insufficient_images_returns_400`
- `test_register_duplicate_chn_returns_409`
- `test_register_invalid_analysis_request_returns_400`
- `test_register_persists_analysis_requests`
- `test_register_supervisor_can_register`

### `apps/samples/tests/test_services.py`

**TestSampleRegistrationService** — 7 pruebas

- `test_register_complete_creates_sample_and_vault`
- `test_register_draft_only_requires_chn`
- `test_register_draft_without_patient_skips_vault`
- `test_register_duplicate_chn_raises`
- `test_register_generates_sequential_sample_codes`
- `test_register_atomic_rollback_on_failure`
- `test_register_skips_malformed_image`

### `apps/samples/tests/test_shared_jwt_auth.py`

**TestGetUser** — 7 pruebas

- `test_token_sin_email_claim_rechazado`
- `test_usuario_nuevo_se_crea_automaticamente`
- `test_usuario_existente_se_reutiliza_no_duplica`
- `test_sincroniza_is_staff_is_superuser_admin`
- `test_sincroniza_is_staff_supervisor_sin_superuser`
- `test_sincroniza_analista_sin_staff_ni_superuser`
- `test_cambio_de_role_se_refleja_en_siguiente_request_sin_recrear_usuario`

**TestEndpointsLoginClinicEliminados** — 2 pruebas

- `test_login_clinic_ya_no_existe`
- `test_refresh_clinic_ya_no_existe`

**TestIntegracionConRBAC** — 1 prueba

- `test_tiene_opcion_funciona_sobre_usuario_sincronizado_por_sso`

### `apps/samples/tests/test_supervisor_s1.py`

**TestAuditSelection** — 4 pruebas

- `test_selects_five_percent_min_one`
- `test_selection_is_deterministic`
- `test_pool_excludes_low_confidence`
- `test_no_karyotype_returns_empty`

**TestAuditDecision** — 4 pruebas

- `test_decide_confirms_and_emits_event`
- `test_decide_invalid_rejected`
- `test_decide_requires_analyst_validated`
- `test_summary_counts`

**TestAuditEndpoints** — 5 pruebas

- `test_supervisor_lists_selection`
- `test_supervisor_decides`
- `test_decide_unknown_chromosome_404`
- `test_analyst_forbidden_by_segregation`
- `test_anonimo_401`

### `apps/samples/tests/test_supervisor_s2.py`

**TestSignService** — 7 pruebas

- `test_sign_success`
- `test_segregation_blocks_analyst_signer`
- `test_gate_blocks_incomplete_audit`
- `test_not_signable_when_not_validated`
- `test_not_enrolled`
- `test_invalid_mfa_increments_and_locks_after_three`
- `test_success_resets_lockout`

**TestSignEndpoint** — 5 pruebas

- `test_supervisor_signs`
- `test_gate_returns_409`
- `test_invalid_mfa_returns_401`
- `test_mfa_service_down_returns_503`
- `test_analyst_forbidden_by_permission`

### `apps/samples/tests/test_tiene_opcion.py`

**TestFailClosed** — 3 pruebas

- `test_opcion_inexistente_fail_closed`
- `test_sin_grupo_sin_privilegio`
- `test_grupo_asignado_sin_privilegio_definido_para_la_opcion`

**TestResolucionPorGrupo** — 5 pruebas

- `test_un_grupo_permite`
- `test_un_grupo_deniega`
- `test_dos_grupos_ambos_permiten`
- `test_dos_grupos_uno_permite_uno_deniega_gana_denegacion`
- `test_usuario_en_multiples_grupos_admin_y_analista_gana_denegacion`

**TestExcepcionIndividual** — 4 pruebas

- `test_excepcion_true_sobre_grupo_false`
- `test_excepcion_false_sobre_grupo_true`
- `test_excepcion_none_usa_grupo`
- `test_excepcion_sin_ningun_grupo`

### `apps/samples/tests/test_tool_router.py`

**TestEscenario1Controlado** — 4 pruebas

- `test_resuelve_por_palabra_clave`
- `test_declara_de_qué_tabla_salió_el_dato`
- `test_no_llama_al_modelo`
- `test_devuelve_los_datos_reales_de_la_base`

**TestEscenario2Sinonimo** — 4 pruebas

- `test_ninguna_palabra_clave_coincide`
- `test_el_modelo_elige_la_herramienta`
- `test_devuelve_EXACTAMENTE_lo_mismo_que_el_escenario_1`
- `test_expone_por_qué_el_modelo_eligió_esa`

**TestEscenario3FueraDeAlcance** — 4 pruebas

- `test_dice_que_no_sabe`
- `test_publica_lo_que_sí_puede_responder`
- `test_no_inventa_datos`
- `test_un_nombre_inexistente_se_trata_como_NINGUNA`

**TestEscenario4ModeloApagado** — 3 pruebas

- `test_los_datos_salen_igual`
- `test_respuesta_idéntica_a_la_del_escenario_1`
- `test_el_sinónimo_deja_de_funcionar`

**TestDegradaciónYBordes** — 7 pruebas

- `test_el_modelo_caído_no_rompe_la_consulta`
- `test_el_modelo_caído_no_afecta_al_camino_por_palabra_clave`
- `test_consulta_vacía[]`
- `test_consulta_vacía[   ]`
- `test_consulta_vacía[None]`
- `test_sin_resultados_no_es_lo_mismo_que_sin_herramienta`
- `test_gana_la_palabra_clave_más_específica`

**TestCatálogo** — 4 pruebas

- `test_toda_herramienta_declara_su_tabla`
- `test_los_nombres_son_únicos`
- `test_ninguna_palabra_clave_está_repetida_entre_herramientas`
- `test_toda_herramienta_es_ejecutable`

**TestEndpoint** — 5 pruebas

- `test_responde_con_la_procedencia_del_dato`
- `test_fuera_de_alcance_es_200_no_error`
- `test_con_la_ia_apagada_sigue_respondiendo`
- `test_get_publica_el_catalogo`
- `test_anonimo_rechazado`

**TestTruncado** — 3 pruebas

- `test_por_debajo_del_tope_no_advierte`
- `test_en_el_tope_advierte_que_puede_haber_mas`
- `test_sin_filas_no_habla_de_truncado`

### `apps/samples/tests/test_views.py`

**TestSampleListCreate** — 5 pruebas

- `test_create_sample_success`
- `test_create_duplicate_chn_rejected`
- `test_create_unauthenticated_rejected`
- `test_list_scoped_to_analyst`
- `test_list_supervisor_sees_all`

**TestSampleListFilters** — 5 pruebas

- `test_filtro_status`
- `test_filtro_chn_query_contains`
- `test_filtro_fecha_rango`
- `test_filtros_combinados_analista_scoped`
- `test_sin_filtros_retorna_todas_las_scoped`

### `apps/samples/tests/test_agente_grafo.py`

**TestTrazaCompatibleConNivel4** — 5 pruebas

- `test_registra_pregunta_accion_observacion_y_respuesta`
- `test_suma_los_tokens_de_todas_las_llamadas`
- `test_una_llamada_sin_uso_declarado_no_rompe_el_conteo`
- `test_la_accion_lleva_el_nombre_y_los_argumentos`
- `test_varias_herramientas_en_un_paso_dan_varias_acciones`

**TestSoloElTurnoActual** — 2 pruebas

- `test_los_mensajes_previos_no_entran_en_la_traza`
- `test_un_hilo_vacio_da_una_traza_vacia`

**TestFrenoYDegradacion** — 2 pruebas

- `test_el_limite_del_grafo_conserva_el_presupuesto_del_nivel_4`
- `test_sin_IA_no_revienta_lanza_AgenteError`

**TestSeparacionDeLaBaseClinica** — 1 prueba

- `test_la_memoria_NO_vive_en_la_base_clinica`

**TestElGrafoEncadena** — 3 pruebas

- `test_pide_herramienta_la_ejecuta_y_vuelve_a_pensar`
- `test_sin_herramientas_responde_y_corta`
- `test_un_error_de_la_herramienta_llega_como_observacion`

**TestMemoriaPersistente** — 4 pruebas

- `test_el_segundo_turno_VE_el_primero`
- `test_hilos_distintos_no_se_mezclan`
- `test_el_system_prompt_se_inyecta_UNA_vez`
- `test_olvidar_borra_el_hilo`

**TestElFrenoDeVerdad** — 1 prueba

- `test_un_modelo_que_nunca_para_se_corta_y_lo_dice`

### `apps/samples/tests/test_corpus.py`

**TestBusquedaPorClave** — 11 pruebas

- `test_recupera_lo_que_corresponde[47,XY,+21-claves0]`
- `test_recupera_lo_que_corresponde[47,XX,+18-claves1]`
- `test_recupera_lo_que_corresponde[47,XY,+13-claves2]`
- `test_recupera_lo_que_corresponde[45,X-claves3]`
- `test_recupera_lo_que_corresponde[47,XXY-claves4]`
- `test_recupera_lo_que_corresponde[48,XX,+13,+21-claves5]`
- `test_recupera_lo_que_corresponde[45,XX,-22-claves6]`
- `test_recupera_lo_que_corresponde[46,XX-claves7]`
- `test_el_sexo_va_primero`
- `test_una_anomalia_repetida_no_duplica_el_contexto`
- `test_solo_mira_la_primera_linea_del_mosaico`

**TestCoberturaParcial** — 5 pruebas

- `test_una_anomalia_sin_entrada_no_rompe_la_busqueda`
- `test_un_iscn_irreconocible_devuelve_vacio_sin_lanzar[]`
- `test_un_iscn_irreconocible_devuelve_vacio_sin_lanzar[   ]`
- `test_un_iscn_irreconocible_devuelve_vacio_sin_lanzar[basura]`
- `test_un_iscn_irreconocible_devuelve_vacio_sin_lanzar[None]`

**TestEstadoDeRevision** — 3 pruebas

- `test_las_entradas_semilla_estan_sin_revisar`
- `test_la_auditoria_cuenta_lo_que_no_esta_firmado`
- `test_la_auditoria_de_un_caso_sin_corpus_es_cero`

**TestProcedencia** — 3 pruebas

- `test_toda_entrada_cita_su_fuente`
- `test_toda_entrada_tiene_nombre_y_descripcion`
- `test_la_clave_coincide_con_su_indice`

**TestFormatoParaPrompt** — 3 pruebas

- `test_se_rotula_como_referencia_no_como_texto_a_copiar`
- `test_incluye_la_descripcion_de_lo_recuperado`
- `test_sin_entradas_no_ensucia_el_prompt`

**TestCorpusEnElPrompt** — 4 pruebas

- `test_la_referencia_llega_al_prompt`
- `test_el_iscn_sigue_presente`
- `test_sin_corpus_el_prompt_sigue_siendo_valido`
- `test_el_prompt_no_lleva_pii`

### `apps/samples/tests/test_iscn.py`

**TestCariotiposNormales** — 2 pruebas

- `test_femenino`
- `test_masculino`

**TestSindromesReales** — 7 pruebas

- `test_down_trisomia_21`
- `test_edwards_trisomia_18`
- `test_patau_trisomia_13`
- `test_turner_monosomia_x`
- `test_klinefelter_xxy`
- `test_klinefelter_con_trisomia_21`
- `test_monosomia_autosomica`

**TestOrdenDeAnomalias** — 3 pruebas

- `test_18_antes_que_21`
- `test_un_digito_antes_que_dos_digitos`
- `test_ganancia_doble_se_repite`

**TestEntradasInvalidas** — 4 pruebas

- `test_conteo_vacio_no_inventa_un_cariotipo`
- `test_none_no_revienta`
- `test_sin_sexuales_es_incompleto`
- `test_ignora_ceros`

**TestDeterminismo** — 3 pruebas

- `test_mismo_input_mismo_output`
- `test_el_orden_de_las_claves_no_importa`
- `test_no_muta_la_entrada`

**TestValidacionDeOverride** — 43 pruebas

- `test_acepta_nomenclatura_del_estandar[46,XX]`
- `test_acepta_nomenclatura_del_estandar[46,XY]`
- `test_acepta_nomenclatura_del_estandar[46,U]`
- `test_acepta_nomenclatura_del_estandar[45,X]`
- `test_acepta_nomenclatura_del_estandar[48,XXXY]`
- `test_acepta_nomenclatura_del_estandar[47,XX,+21]`
- `test_acepta_nomenclatura_del_estandar[46,XX,+8,-21]`
- `test_acepta_nomenclatura_del_estandar[46,XX,del(5)(q13)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,del(5)(q13q33)]`
- `test_acepta_nomenclatura_del_estandar[46,XY,t(9;22)(q34;q11.2)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,inv(2)(p23p13)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,i(17)(q10)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,r(7)(p15q31)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,add(19)(p13.3)]`
- `test_acepta_nomenclatura_del_estandar[45,XX,dic(13;15)(q22;q24)]`
- `test_acepta_nomenclatura_del_estandar[46,XY,der(1)t(1;3)(p22;q13.1)]`
- `test_acepta_nomenclatura_del_estandar[47,XX,+mar]`
- `test_acepta_nomenclatura_del_estandar[47,XX,+der(5)t(2;5)(q21;q31)]`
- `test_acepta_nomenclatura_del_estandar[45,XY,psu dic(15;13)(q12;q12)]`
- `test_acepta_nomenclatura_del_estandar[46,X,fra(X)(q27.3)]`
- `test_acepta_nomenclatura_del_estandar[46,XX,del(6)(q13q23)x2]`
- `test_acepta_mosaicismo_y_recuentos[45,X[13]/46,XY[17]]`
- `test_acepta_mosaicismo_y_recuentos[mos 47,XXY[10]/46,XY[20]]`
- `test_acepta_mosaicismo_y_recuentos[46,XX[5]//46,XY[25]]`
- `test_acepta_mosaicismo_y_recuentos[45~48,XX,+8[cp10]]`
- `test_acepta_mosaicismo_y_recuentos[47,XY,+mar dn[14]/46,XY[16]]`
- `test_acepta_sufijos_y_dudas[47,XX,+21c]`
- `test_acepta_sufijos_y_dudas[46,XX,t(5;6)(q34;q23)mat]`
- `test_acepta_sufijos_y_dudas[46,XY,?del(1)(p36.1)]`
- `test_acepta_sufijos_y_dudas[47,XX,+?8]`
- `test_preserva_el_espacio_significativo`
- `test_normaliza_espacios`
- `test_rechaza_basura[]`
- `test_rechaza_basura[   ]`
- `test_rechaza_basura[cuarenta y seis]`
- `test_rechaza_basura[46]`
- `test_rechaza_basura[XX]`
- `test_rechaza_basura[46-XX]`
- `test_rechaza_basura[46,ZZ]`
- `test_rechaza_basura[46,XX,]`
- `test_rechaza_basura[DROP TABLE samples]`
- `test_rechaza_recuento_fuera_de_rango`
- `test_none_no_revienta`

**TestRoundTrip** — 6 pruebas

- `test_generado_es_valido[mods0]`
- `test_generado_es_valido[mods1]`
- `test_generado_es_valido[mods2]`
- `test_generado_es_valido[mods3]`
- `test_generado_es_valido[mods4]`
- `test_generado_es_valido[mods5]`

**TestConteosQueProducirianUnIscnFalso** — 7 pruebas

- `test_una_clase_desconocida_no_infla_el_recuento_en_silencio`
- `test_es_alcanzable_desde_el_pipeline`
- `test_clase_vacia_rechazada`
- `test_el_mensaje_nombra_la_clase_culpable`
- `test_conteo_negativo_rechazado`
- `test_recuento_fuera_de_rango_biologico`
- `test_el_generador_nunca_produce_algo_que_su_validador_rechace`

**TestGeneraNomenclaturaDelEstandar** — 10 pruebas

- `test_complemento_sexual[sexo_counts0-45,X-\xa75.3.1.1 i   Turner]`
- `test_complemento_sexual[sexo_counts1-47,XXX-\xa75.3.1.1 ii  triple X]`
- `test_complemento_sexual[sexo_counts2-47,XYY-\xa75.3.1.1 iii XYY]`
- `test_complemento_sexual[sexo_counts3-48,XXXY-\xa75.3.1.1 iv  XXXY]`
- `test_complemento_sexual[sexo_counts4-47,XXY-\xa74.2.1 e     Klinefelter]`
- `test_anomalias_autosomicas[mods0-47,XX,+21-\xa75.3.2 i   Down]`
- `test_anomalias_autosomicas[mods1-48,XX,+13,+21-\xa75.3.2 ii  doble trisom\xeda]`
- `test_anomalias_autosomicas[mods2-45,XX,-22-\xa75.3.2 iii monosom\xeda 22]`
- `test_anomalias_autosomicas[mods3-46,XX,+8,-21-\xa75.3.2 iv  ganancia y p\xe9rdida]`
- `test_anomalias_autosomicas[mods4-48,XX,+8,+8-tabla 8 #17 tetrasom\xeda]`

### `apps/samples/tests/test_llm_client.py`

**TestGeneracionNarrativa** — 3 pruebas

- `test_camino_feliz_devuelve_texto_y_metricas`
- `test_acepta_anomalia_que_si_esta_en_el_iscn`
- `test_apagado_por_settings_no_llama_al_modelo`

**TestDefensaContraAlucinacion** — 9 pruebas

- `test_rechaza_trisomia_inventada`
- `test_rechaza_anomalia_estructural_inventada`
- `test_rechaza_anomalia_de_otro_cromosoma`
- `test_una_alucinacion_no_abre_el_circuito`
- `test_rechaza_lo_que_no_cumple_el_esquema[]`
- `test_rechaza_lo_que_no_cumple_el_esquema[El cariotipo es normal.]`
- `test_rechaza_lo_que_no_cumple_el_esquema[{"hallazgo": "corto", "interpretacion": "x", "es_normal": true}]`
- `test_rechaza_lo_que_no_cumple_el_esquema[{"hallazgo": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}]`
- `test_none_del_modelo_no_revienta`

**TestSinPiiEnElPrompt** — 2 pruebas

- `test_el_prompt_solo_lleva_chn_iscn_tipo_y_conteo`
- `test_temperatura_baja_para_registro_clinico`

**TestDegradacionYCircuitBreaker** — 4 pruebas

- `test_servicio_caido_lanza_error_manejable`
- `test_el_circuito_abre_tras_el_umbral`
- `test_el_exito_resetea_los_fallos`
- `test_sin_sdk_instalado_degrada`

**TestSalidaEstructurada** — 3 pruebas

- `test_devuelve_el_objeto_validado`
- `test_el_texto_plano_sale_del_objeto`
- `test_pide_el_esquema_a_la_api`

**TestCicloDeReintento** — 8 pruebas

- `test_reintenta_cuando_devuelve_prosa`
- `test_reintenta_cuando_falta_un_campo`
- `test_reintenta_cuando_alucina`
- `test_le_pasa_el_error_al_modelo`
- `test_agota_los_intentos_y_falla`
- `test_agotar_intentos_no_abre_el_circuito`
- `test_acumula_los_tokens_de_todos_los_intentos`
- `test_max_intentos_configurable`

### `apps/samples/tests/test_llm_schemas.py`

**TestContratoDeTipos** — 13 pruebas

- `test_objeto_valido`
- `test_nivel_confianza_por_defecto`
- `test_campos_obligatorios[hallazgo]`
- `test_campos_obligatorios[interpretacion]`
- `test_campos_obligatorios[es_normal]`
- `test_rechaza_texto_demasiado_corto`
- `test_rechaza_texto_desbordado`
- `test_rechaza_nivel_de_confianza_inventado`
- `test_rechaza_tipo_incorrecto`
- `test_normaliza_espacios`
- `test_limpia_las_anomalias`
- `test_parsea_desde_json`
- `test_prosa_en_vez_de_json_no_valida`

**TestCoherenciaConElIscn** — 10 pruebas

- `test_acepta_anomalia_presente_en_el_iscn`
- `test_bloquea_trisomia_inventada`
- `test_bloquea_anomalia_de_otro_cromosoma`
- `test_bloquea_estructural_inventada`
- `test_acepta_estructural_presente`
- `test_bloquea_normal_declarado_sobre_iscn_con_anomalias`
- `test_bloquea_anormal_declarado_sobre_iscn_normal`
- `test_cariotipo_normal_coherente`
- `test_ignora_espacios_y_mayusculas`
- `test_turner_es_normal_estructuralmente`

**TestTextoPlano** — 1 prueba

- `test_concatena_hallazgo_e_interpretacion`

**TestEsquemaJson** — 3 pruebas

- `test_declara_strict`
- `test_no_admite_campos_extra`
- `test_declara_los_campos_requeridos`

### `apps/samples/tests/test_mcp_conexion.py`

**TestTraduccionDeSchema** — 5 pruebas

- `test_envuelve_el_schema_sin_tocarlo`
- `test_acepta_inputSchema_y_input_schema`
- `test_sin_schema_declara_un_objeto_vacio_valido`
- `test_la_descripcion_se_limpia_porque_ES_el_prompt`
- `test_una_descripcion_vacia_no_rompe_la_traduccion`

**TestDescubrimiento** — 2 pruebas

- `test_traduce_todo_lo_que_publica_el_servidor`
- `test_un_servidor_sin_herramientas_da_lista_vacia_no_error`

**TestEjecucion** — 6 pruebas

- `test_devuelve_el_JSON_que_produjo_la_herramienta`
- `test_pasa_el_nombre_y_los_argumentos_al_servidor`
- `test_sin_argumentos_manda_un_dict_vacio_no_None`
- `test_junta_los_bloques_de_texto`
- `test_una_respuesta_que_no_es_JSON_se_devuelve_como_texto`
- `test_una_respuesta_vacia_no_lanza`

**TestContratoDeErrores** — 2 pruebas

- `test_un_fallo_del_servidor_vuelve_como_dict_no_como_excepcion`
- `test_usar_la_conexion_sin_abrir_lo_dice_claro`

**TestCicloDeVidaDelHilo** — 5 pruebas

- `test_abre_el_hilo_al_entrar_y_lo_para_al_salir`
- `test_una_excepcion_dentro_del_with_no_deja_el_hilo_colgado`
- `test_un_fallo_al_cerrar_no_enmascara_el_error_original`
- `test_el_esperar_REAL_despacha_al_bucle_del_hilo`
- `test_un_fallo_dentro_de_la_corrutina_sale_como_McpError`

### `apps/samples/tests/test_pipeline_client.py`

**TestPipelineClient** — 5 pruebas

- `test_trigger_processing_success`
- `test_trigger_processing_timeout_raises_degraded`
- `test_circuit_opens_after_threshold_failures`
- `test_get_status_success`
- `test_get_status_error_raises_degraded`

### `apps/samples/tests/test_rag_corpus.py`

**TestJerarquiaDeSecciones** — 3 pruebas

- `test_cada_fragmento_conoce_su_seccion`
- `test_la_subseccion_no_arrastra_a_su_hermana`
- `test_el_texto_embebido_lleva_fuente_y_seccion`

**TestSolape** — 2 pruebas

- `test_los_trozos_de_una_seccion_larga_comparten_texto`
- `test_sin_solape_los_trozos_siguen_cubriendo_el_texto`

**TestDescartes** — 3 pruebas

- `test_las_secciones_vacias_no_generan_fragmento`
- `test_los_fragmentos_demasiado_cortos_se_descartan`
- `test_ningun_fragmento_baja_del_minimo`

**TestOrdenYClave** — 2 pruebas

- `test_el_orden_es_correlativo_dentro_del_documento`
- `test_la_clave_identifica_al_fragmento`

### `apps/samples/tests/test_rag_sugerencias.py`

**TestCuandoElCorpusNoResponde** — 2 pruebas

- `test_un_no_se_deja_de_ser_un_callejon_sin_salida`
- `test_el_texto_NO_promete_que_eso_responda`

**TestCuandoElCorpusSiResponde** — 3 pruebas

- `test_no_repite_lo_que_ya_se_cito`
- `test_otra_seccion_del_MISMO_documento_si_se_sugiere`
- `test_son_de_tipo_ampliar`

**TestQueSeAgrupaEnCadaCaso** — 2 pruebas

- `test_explorando_NO_se_repite_documento`
- `test_ampliando_SI_puede_repetirse_documento`

**TestSeccionLegible** — 5 pruebas

- `test_se_queda_con_el_ultimo_tramo_de_la_miga_de_pan`
- `test_quita_los_escapes_de_markdown`
- `test_una_seccion_normal_no_se_toca`
- `test_sin_seccion_devuelve_vacio`
- `test_la_sugerencia_muestra_la_seccion_ya_limpia`

**TestComparacionDeSimilitud** — 4 pruebas

- `test_van_de_mayor_a_menor_parecido`
- `test_no_repite_la_misma_seccion_dos_veces`
- `test_se_corta_en_el_maximo`
- `test_el_porcentaje_se_muestra_como_lo_pide_la_consigna`

**TestBordes** — 4 pruebas

- `test_sin_candidatos_no_hay_sugerencias`
- `test_sin_sugerencias_el_texto_es_vacio`
- `test_si_todo_lo_recuperado_ya_se_cito_no_sobra_nada`
- `test_un_fragmento_sin_seccion_se_muestra_solo_con_el_documento`

**TestSerializacion** — 4 pruebas

- `test_as_dict_lleva_documento_seccion_y_similitud`
- `test_una_seccion_vacia_se_muestra_con_guion`
- `test_la_sugerencia_es_inmutable`
- `test_el_tipo_declarado_es_uno_de_los_dos`

---

## 3 · `backend-admin` — 345 unit tests

### `apps/audit/tests/test_audit_endpoint.py`

**TestAuditEndpointAuth** — 4 pruebas

- `test_anon_returns_401`
- `test_supervisor_get_allowed`
- `test_analista_get_allowed`
- `test_admin_returns_200`

**TestAuditEndpointPayload** — 2 pruebas

- `test_response_shape`
- `test_results_is_list`

**TestAuditEndpointFilters** — 6 pruebas

- `test_filter_by_action_create`
- `test_filter_by_action_update`
- `test_filter_by_model`
- `test_invalid_action_filter_ignored`
- `test_pagination_limit`
- `test_pagination_offset`

### `apps/audit/tests/test_auditlog_signal.py`

**TestAdminUserAudit** — 4 pruebas

- `test_create_generates_log_entry`
- `test_update_generates_log_entry`
- `test_soft_delete_generates_log_entry`
- `test_log_entry_records_changes`

**TestUserAudit** — 2 pruebas

- `test_user_creation_generates_log_entry`
- `test_user_role_change_audited`

### `apps/config/tests/test_ai_models.py`

**TestModelConfig** — 7 pruebas

- `test_singleton_constraint_prevents_two_active`
- `test_two_inactive_rows_allowed`
- `test_compliance_warning_true_below_threshold`
- `test_compliance_warning_false_at_or_above_threshold`
- `test_str_representation`
- `test_invalid_analysis_mode_rejected_by_constraint`
- `test_confidence_out_of_range_rejected_by_constraint`

**TestModelMetric** — 2 pruebas

- `test_str_representation`
- `test_ordering_most_recent_first`

**TestModelConfigSerializer** — 4 pruebas

- `test_compliance_warning_reflects_model_property`
- `test_validate_confidence_threshold_rejects_out_of_range`
- `test_validate_detection_sensitivity_rejects_out_of_range`
- `test_is_active_is_read_only`

**TestModelMetricSerializer** — 2 pruebas

- `test_serializes_all_fields`
- `test_rejects_missing_required_field`

**TestModelConfigView** — 12 pruebas

- `test_get_creates_singleton_if_missing`
- `test_get_idempotent`
- `test_patch_updates_confidence_threshold`
- `test_patch_updates_detection_sensitivity`
- `test_confidence_below_0_85_sets_compliance_warning`
- `test_confidence_at_0_85_no_compliance_warning`
- `test_patch_sets_updated_by`
- `test_patch_invalid_analysis_mode_rejected`
- `test_patch_requires_admin_role`
- `test_get_allowed_for_non_admin_authenticated`
- `test_get_without_auth_returns_401`
- `test_patch_without_auth_returns_401`

**TestModelMetricViews** — 10 pruebas

- `test_post_creates_snapshot`
- `test_post_requires_admin_role`
- `test_metrics_append_only_no_patch_no_delete`
- `test_metrics_endpoint_filters_by_days`
- `test_metrics_days_param_clamped_below_minimum`
- `test_metrics_days_param_clamped_above_maximum`
- `test_metrics_days_param_non_numeric_falls_back_to_default`
- `test_latest_returns_204_when_empty`
- `test_latest_returns_most_recent`
- `test_metrics_list_without_auth_returns_401`

**(funciones sueltas)** — 2 pruebas

- `test_health_view_includes_modelos_section`
- `test_validation_error_response_without_message_dict_uses_detail`

### `apps/config/tests/test_appearance.py`

**TestAppearancePreferenceModel** — 7 pruebas

- `test_defaults`
- `test_str_representation`
- `test_one_to_one_constraint`
- `test_invalid_theme_rejected_by_constraint`
- `test_invalid_density_rejected_by_constraint`
- `test_invalid_language_rejected_by_constraint`
- `test_invalid_font_size_rejected_by_constraint`

**TestAppearancePreferenceSerializer** — 3 pruebas

- `test_serializes_all_fields`
- `test_rejects_invalid_theme_choice`
- `test_id_and_updated_at_read_only`

**TestMeAppearanceView** — 7 pruebas

- `test_get_creates_preferences_if_missing`
- `test_get_idempotent`
- `test_patch_updates_theme_and_density`
- `test_patch_invalid_theme_rejected`
- `test_patch_persists_to_db`
- `test_get_without_auth_returns_401`
- `test_patch_without_auth_returns_401`

**(funciones sueltas)** — 1 prueba

- `test_health_view_includes_appearance_section`

### `apps/config/tests/test_health.py`

**ConfigHealthTests** — 2 pruebas

- `test_health_does_not_require_auth`
- `test_health_endpoint_returns_ok`

### `apps/config/tests/test_internal_mfa.py`

**TestInternalMfaVerify** — 6 pruebas

- `test_valid_code_returns_valid_true`
- `test_invalid_code_returns_valid_false`
- `test_user_without_2fa_reports_not_enrolled`
- `test_unknown_user_returns_not_enrolled`
- `test_wrong_service_secret_forbidden`
- `test_missing_service_secret_forbidden`

### `apps/config/tests/test_notifications.py`

**TestNotificationPreferenceModel** — 3 pruebas

- `test_str_representation`
- `test_defaults`
- `test_one_to_one_constraint`

**TestNotificationPreferenceSerializer** — 2 pruebas

- `test_serializes_all_fields`
- `test_id_and_updated_at_read_only`

**TestMeNotificationsView** — 8 pruebas

- `test_get_creates_preferences_if_missing`
- `test_get_idempotent`
- `test_get_on_creation_returns_normalized_time_format`
- `test_patch_updates_email_preference`
- `test_patch_updates_quiet_hours`
- `test_patch_persists_to_db`
- `test_get_without_auth_returns_401`
- `test_patch_without_auth_returns_401`

**(funciones sueltas)** — 1 prueba

- `test_health_view_includes_notifications_section`

### `apps/config/tests/test_profile.py`

**TestValidators** — 10 pruebas

- `test_validate_full_name_accepts_valid`
- `test_validate_full_name_rejects_too_short`
- `test_validate_full_name_rejects_too_long`
- `test_validate_full_name_rejects_empty`
- `test_normalize_email_lowercases_and_strips`
- `test_validate_phone_accepts_e164_like`
- `test_validate_phone_accepts_empty`
- `test_validate_phone_rejects_garbage`
- `test_email_regex_matches_basic`
- `test_phone_regex_basic`

**TestAdminProfileModel** — 8 pruebas

- `test_str_returns_email`
- `test_save_normalizes_email`
- `test_save_strips_full_name`
- `test_save_rejects_too_short_name`
- `test_save_rejects_bad_email`
- `test_save_rejects_bad_phone`
- `test_save_allows_blank_phone`
- `test_db_table_uses_admin_profiles_prefix`

**TestAdminProfileSerializer** — 6 pruebas

- `test_serializes_all_fields`
- `test_read_only_fields_not_accepted_on_input`
- `test_validate_full_name_runs`
- `test_validate_email_normalizes`
- `test_validate_phone_runs`
- `test_blank_phone_accepted`

**TestMeProfileView** — 11 pruebas

- `test_get_creates_profile_if_missing`
- `test_get_idempotent`
- `test_get_returns_existing_profile`
- `test_patch_updates_profile`
- `test_patch_persists_to_db`
- `test_patch_rejects_short_name`
- `test_patch_rejects_bad_email`
- `test_patch_rejects_bad_phone`
- `test_get_without_auth_returns_401`
- `test_patch_without_auth_returns_401`
- `test_audit_log_entry_created_on_patch`

**TestIsOwnerOrAdmin** — 5 pruebas

- `test_anonymous_denied`
- `test_authenticated_user_has_permission`
- `test_admin_can_edit_any_profile`
- `test_user_can_edit_own_profile`
- `test_user_cannot_edit_other_profile`

### `apps/config/tests/test_security.py`

**TestRotatePassword** — 10 pruebas

- `test_wrong_current_rejected`
- `test_mismatch_confirm_rejected`
- `test_too_short_rejected`
- `test_missing_uppercase_rejected`
- `test_missing_digit_rejected`
- `test_rejects_reuse_of_current_password`
- `test_rejects_reuse_of_recent_history`
- `test_history_depth_respected`
- `test_success_updates_password_and_timestamp`
- `test_success_creates_password_history_entry`

**TestSetup2FA** — 3 pruebas

- `test_generates_secret_and_qr`
- `test_secret_persisted_encrypted_not_plain`
- `test_setup_rotates_previous_secret`

**TestToggle2FA** — 5 pruebas

- `test_enable_with_valid_code_succeeds`
- `test_enable_with_invalid_code_rejected`
- `test_disable_requires_valid_code`
- `test_disable_with_valid_code_succeeds`
- `test_toggle_without_2fa_configured_raises`

**TestVerifyTotpCode** — 3 pruebas

- `test_verify_returns_false_without_secret`
- `test_verify_returns_true_for_valid_code`
- `test_verify_returns_false_for_invalid_code`

**TestChangePasswordSerializer** — 2 pruebas

- `test_valid_payload`
- `test_missing_field_rejected`

**TestAdminProfileSerializerTwoFactorField** — 2 pruebas

- `test_two_factor_enabled_reflects_user_state`
- `test_two_factor_enabled_read_only_ignored_on_input`

**TestTwoFactorToggleSerializer** — 2 pruebas

- `test_valid_payload`
- `test_code_wrong_length_rejected`

**TestChangePasswordView** — 4 pruebas

- `test_success_returns_200`
- `test_wrong_current_returns_400`
- `test_missing_fields_returns_400`
- `test_without_auth_returns_401`

**TestTwoFactorSetupView** — 2 pruebas

- `test_success_returns_secret_and_qr`
- `test_without_auth_returns_401`

**TestTwoFactorToggleView** — 4 pruebas

- `test_enable_with_valid_code_returns_200`
- `test_invalid_code_returns_400`
- `test_missing_fields_returns_400`
- `test_without_auth_returns_401`

**TestEncryptedCharField** — 5 pruebas

- `test_round_trip_via_orm`
- `test_blank_value_not_encrypted`
- `test_get_prep_value_encrypts`
- `test_from_db_value_passthrough_on_non_token`
- `test_decrypt_totp_secret_handles_plain_fallback`

**TestPasswordHistoryModel** — 2 pruebas

- `test_str_representation`
- `test_ordering_most_recent_first`

### `apps/users/tests/test_auth_bridge.py`

**TestExchangeHappyPath** — 4 pruebas

- `test_creates_user_and_token`
- `test_returns_existing_token_for_existing_user`
- `test_email_lowercased`
- `test_role_synced_on_existing_user`

**TestExchangeFailures** — 5 pruebas

- `test_expired_signature_raises`
- `test_wrong_signature_raises`
- `test_missing_required_claim_raises`
- `test_invalid_role_raises`
- `test_algorithm_confusion_raises`

**TestTokenReuse** — 2 pruebas

- `test_returns_same_token_on_subsequent_calls`
- `test_different_emails_different_tokens`

### `apps/users/tests/test_auth_bridge_e2e.py`

**TestE2EHappyPath** — 3 pruebas

- `test_login_exchange_then_list_users`
- `test_exchange_creates_admin_user_in_domain`
- `test_exchange_is_idempotent_for_same_email`

**TestE2EFailures** — 7 pruebas

- `test_missing_bearer_header_returns_401`
- `test_wrong_auth_scheme_returns_401`
- `test_expired_jwt_returns_401`
- `test_invalid_signature_returns_401`
- `test_invalid_role_returns_401`
- `test_missing_required_claim_returns_401`
- `test_malformed_jwt_returns_401`

**TestE2EPostExchange** — 2 pruebas

- `test_admin_can_create_user_after_exchange`
- `test_non_admin_role_cannot_create_user`

### `apps/users/tests/test_auth_login.py`

**TestLoginSuccess** — 4 pruebas

- `test_login_returns_access_refresh_role_email`
- `test_login_full_name_null_without_admin_profile`
- `test_login_full_name_present_with_admin_profile`
- `test_login_analista_role`

**TestLoginFailure** — 4 pruebas

- `test_wrong_password_401`
- `test_nonexistent_email_401_same_message`
- `test_inactive_user_401`
- `test_missing_password_400`

### `apps/users/tests/test_auth_logout.py`

**TestLogout** — 6 pruebas

- `test_logout_requires_auth`
- `test_logout_blacklists_refresh`
- `test_refresh_fails_after_logout`
- `test_logout_missing_refresh_400`
- `test_logout_invalid_refresh_400`
- `test_logout_twice_second_is_400`

**TestRefresh** — 2 pruebas

- `test_refresh_returns_new_access`
- `test_refresh_rotates_refresh_token`

### `apps/users/tests/test_auth_me.py`

**TestMe** — 3 pruebas

- `test_me_requires_auth`
- `test_me_returns_current_user_data`
- `test_me_rejects_invalid_token`

### `apps/users/tests/test_auth_serializers.py`

**TestFullNameFor** — 2 pruebas

- `test_returns_full_name_when_admin_profile_exists`
- `test_returns_none_when_no_admin_profile`

**TestMeSerializer** — 1 prueba

- `test_from_user_shape`

**TestAdminTokenObtainPairSerializerGetToken** — 2 pruebas

- `test_get_token_incluye_email_y_role_como_claims`
- `test_get_token_conserva_claims_default_de_simplejwt`

### `apps/users/tests/test_models.py`

**TestReactivate** — 3 pruebas

- `test_reactivate_resets_deactivated_at`
- `test_reactivate_also_reactivates_user`
- `test_reactivate_already_active_raises`

**TestCleanMethod** — 4 pruebas

- `test_clean_rejects_invalid_role`
- `test_clean_normalizes_email`
- `test_clean_normalizes_full_name`
- `test_clean_rejects_short_name`

**TestVendorAwareDbTable** — 2 pruebas

- `test_default_db_table_in_sqlite_is_plain`
- `test_postgres_engine_returns_schema_qualified`

### `apps/users/tests/test_permissions.py`

**TestIsAdminRole** — 7 pruebas

- `test_anon_denied`
- `test_admin_get_allowed`
- `test_admin_post_allowed`
- `test_supervisor_get_allowed`
- `test_supervisor_post_denied`
- `test_supervisor_delete_denied`
- `test_analista_patch_denied`

**TestIsAdminOrSelf** — 5 pruebas

- `test_admin_can_edit_any_object`
- `test_non_admin_cannot_edit_other_user`
- `test_non_admin_can_edit_self`
- `test_non_admin_no_user_id_attribute_denied`
- `test_anon_denied`

### `apps/users/tests/test_serializers.py`

**TestAdminUserSerializerFields** — 2 pruebas

- `test_includes_expected_fields`
- `test_readonly_fields`

**TestValidateFullName** — 4 pruebas

- `test_valid_full_name_passes`
- `test_strips_whitespace`
- `test_short_name_raises`
- `test_long_name_raises`

**TestValidateEmail** — 2 pruebas

- `test_lowercases`
- `test_strips_whitespace`

**TestValidateRole** — 2 pruebas

- `test_valid_role`
- `test_invalid_role_raises`

**TestValidateUniqueness** — 3 pruebas

- `test_duplicate_email_raises`
- `test_duplicate_case_insensitive_raises`
- `test_self_excluded_from_uniqueness_check`

**TestCreateWithActor** — 2 pruebas

- `test_assigns_created_by_from_request_user`
- `test_no_actor_if_request_user_has_no_adminuser`

**TestCreateSerializer** — 1 prueba

- `test_create_serializer_restricted_fields`

**TestUpdateSerializer** — 3 pruebas

- `test_update_serializer_fields`
- `test_update_serializer_validates_full_name`
- `test_update_serializer_validates_role`

**TestSoftDeleteResponseSerializer** — 1 prueba

- `test_serializes_correctly`

### `apps/users/tests/test_services.py`

**TestCreateAdminUser** — 16 pruebas

- `test_creates_with_valid_data`
- `test_normalizes_email_to_lowercase`
- `test_strips_full_name_whitespace`
- `test_defaults_active_to_true`
- `test_assigns_created_by`
- `test_rejects_short_full_name`
- `test_rejects_long_full_name`
- `test_rejects_invalid_role`
- `test_rejects_duplicate_email`
- `test_rejects_weak_password`
- `test_rejects_password_without_uppercase`
- `test_rejects_password_without_digit`
- `test_creates_linked_authenticatable_user`
- `test_inactive_user_creates_inactive_linked_user`
- `test_admin_role_sets_is_staff_on_linked_user`
- `test_adopts_existing_orphan_user_same_email`

**TestUpdateAdminUser** — 8 pruebas

- `test_updates_full_name`
- `test_updates_role`
- `test_updates_active`
- `test_deactivating_sets_deactivated_at`
- `test_reactivating_clears_deactivated_at`
- `test_no_op_returns_same_instance`
- `test_rejects_invalid_role`
- `test_rejects_short_full_name`

**TestSoftDelete** — 4 pruebas

- `test_soft_delete_sets_deactivated_at`
- `test_soft_delete_idempotent_raises`
- `test_soft_delete_deactivates_associated_user`
- `test_soft_delete_without_user_does_not_fail`

**TestCanDeleteUser** — 3 pruebas

- `test_returns_true_when_current_user_id_none`
- `test_returns_true_for_different_users`
- `test_returns_false_for_self`

**TestValidateEmailFormat** — 6 pruebas

- `test_valid_email_passes`
- `test_uppercase_normalized`
- `test_whitespace_trimmed`
- `test_invalid_format_raises`
- `test_empty_raises`
- `test_none_raises`

### `apps/users/tests/test_views.py`

**TestList** — 3 pruebas

- `test_admin_lists_all_active`
- `test_anon_lists_returns_401`
- `test_list_excludes_soft_deleted`

**TestCreate** — 9 pruebas

- `test_admin_creates_user`
- `test_created_user_can_login`
- `test_create_without_password_returns_400`
- `test_create_with_weak_password_returns_400`
- `test_anon_creates_returns_401`
- `test_supervisor_creates_returns_403`
- `test_duplicate_email_returns_400`
- `test_short_name_returns_400`
- `test_invalid_role_returns_400`

**TestRetrieve** — 2 pruebas

- `test_admin_retrieves`
- `test_not_found_returns_404`

**TestUpdate** — 4 pruebas

- `test_admin_updates_full_name`
- `test_admin_updates_role`
- `test_admin_deactivates`
- `test_supervisor_patch_returns_403`

**TestSoftDelete** — 4 pruebas

- `test_admin_soft_deletes_other_user`
- `test_admin_cannot_delete_self`
- `test_supervisor_delete_returns_403`
- `test_double_delete_returns_404`

**TestHistory** — 2 pruebas

- `test_admin_gets_history`
- `test_history_entries_have_required_fields`

**TestAuthExchange** — 5 pruebas

- `test_missing_bearer_returns_401`
- `test_invalid_jwt_returns_401`
- `test_expired_jwt_returns_401`
- `test_valid_jwt_returns_token`
- `test_jwt_with_invalid_role_returns_401`

### `apps/users/tests/test_views_edges.py`

**TestUpdateSerializerBranch** — 2 pruebas

- `test_partial_update_uses_update_serializer`
- `test_full_update_path`

**TestPartialUpdateFailures** — 2 pruebas

- `test_partial_update_invalid_role`
- `test_partial_update_invalid_full_name`

**TestCreateNoActorBranch** — 1 prueba

- `test_create_when_actor_has_no_adminuser`

**TestCreateErrorBranches** — 3 pruebas

- `test_create_returns_detail_on_unexpected_validation`
- `test_create_returns_dict_when_validation_has_message_dict`
- `test_create_returns_409_on_email_duplicado_string`

**TestPartialUpdateErrorBranches** — 1 prueba

- `test_partial_update_validation_error_400`

**TestDestroyErrorBranches** — 1 prueba

- `test_destroy_validation_error_400`

---

## 4 · `backend-ml` — 44 unit tests

### `tests/test_api.py`

**(funciones sueltas)** — 4 pruebas

- `test_health`
- `test_segment_endpoint`
- `test_segment_rechaza_vacio`
- `test_segment_rechaza_no_imagen`

### `tests/test_asignacion.py`

**(funciones sueltas)** — 11 pruebas

- `test_hungaro_encuentra_el_reparto_optimo`
- `test_hungaro_prefiere_el_total_sobre_la_avaricia`
- `test_hungaro_admite_mas_columnas_que_filas`
- `test_hungaro_rechaza_menos_plazas_que_cromosomas`
- `test_no_prohibe_la_trisomia`
- `test_una_trisomia_debil_si_cede`
- `test_penalizacion_alta_se_comporta_como_cupo_duro`
- `test_corrige_el_exceso_de_copias_que_el_argmax_permite`
- `test_sin_penalizacion_coincide_con_el_argmax_cuando_no_hay_conflicto`
- `test_sin_plazas_suficientes_cae_al_argmax_en_vez_de_fallar`
- `test_sin_cromosomas_no_revienta`

### `tests/test_efficientnet.py`

**TestEfficientNet** — 2 pruebas

- `test_carga_y_clasifica`
- `test_pipeline_usa_el_modelo_entrenado`

**TestCoherenciaDeLosArtefactos** — 3 pruebas

- `test_num_classes_coincide_con_la_lista`
- `test_estan_las_24_clases_esperadas`
- `test_el_orden_corresponde_al_preprocesamiento_declarado`

### `tests/test_preprocess.py`

**TestLetterbox** — 12 pruebas

- `test_salida_es_el_lienzo_cuadrado`
- `test_preserva_la_relacion_de_aspecto`
- `test_preserva_la_escala_relativa`
- `test_invariante_al_zoom_del_microscopio`
- `test_queda_centrado`
- `test_el_relleno_es_fondo_blanco`
- `test_nunca_desborda_el_lienzo`
- `test_sin_referencia_no_revienta[0.0]`
- `test_sin_referencia_no_revienta[-1.0]`
- `test_sin_referencia_no_revienta[None]`
- `test_crop_degenerado_no_revienta`
- `test_acepta_crop_de_3_canales`

**TestReferenceHeight** — 3 pruebas

- `test_es_la_mediana`
- `test_ignora_valores_invalidos`
- `test_lista_vacia_da_cero`

### `tests/test_segmentation.py`

**TestSegmentation** — 4 pruebas

- `test_detecta_los_cromosomas_sinteticos`
- `test_imagen_en_blanco_no_detecta_nada`
- `test_load_gray_decodifica_png`
- `test_load_gray_rechaza_basura`

**TestNucleoInterfasico** — 2 pruebas

- `test_el_nucleo_no_borra_los_cromosomas`
- `test_el_nucleo_no_cambia_el_recuento_de_cromosomas`

**TestPlaceholderClassifier** — 1 prueba

- `test_asigna_clases_por_rango_de_tamano`

**TestPipeline** — 2 pruebas

- `test_pipeline_entrega_estructura_completa`
- `test_pipeline_imagen_vacia`

---

## 5 · `frontend-clinic` — 380 unit tests

### `tests/api/authClient.spec.ts`

**authClient** — 8 pruebas

- `login() guarda access y refresh en localStorage`
- `login() con credenciales vacías lanza excepción`
- `isAuthenticated() es false sin token`
- `isAuthenticated() es true tras login`
- `logout() limpia los tokens`
- `refresh() sin refresh token guardado retorna null`
- `refresh() con refresh token válido actualiza access`
- `refresh() con refresh token inválido hace logout y retorna null`

**renovarSesion (SSO, ADR-0020)** — 7 pruebas

- `sin refresh en el storage compartido devuelve null y no llama a la red`
- `llama a backend-admin, NO a /api/clinic: la autoridad de JWT es admin`
- `guarda el access nuevo en el storage compartido`
- `si el backend rota el refresh, guarda el nuevo: el viejo deja de servir`
- `con refresh caducado devuelve null y NO borra el access vigente`
- `una caída de red devuelve null sin lanzar: se reintenta en el próximo ciclo`
- `una respuesta 200 sin campo access no se da por buena`

**decodeExp** — 3 pruebas

- `lee el exp del token`
- `devuelve null si el token no es un JWT`
- `devuelve null si el payload no trae exp`

### `tests/api/karyotypeClient.spec.ts`

**karyotypeClient** — 3 pruebas

- `get() devuelve el cariotipo con 46 cromosomas y summary`
- `get() sin cariotipo lanza ClinicApiException con code NO_KARYOTYPE (404)`
- `get() muestra inexistente lanza 404 NOT_FOUND`

### `tests/api/registrationClient.spec.ts`

**registrationClient** — 5 pruebas

- `register() exitoso retorna la respuesta parseada`
- `register() con fallo de red lanza ClinicApiException NETWORK_ERROR`
- `register() con respuesta no-JSON usa el texto como detail`
- `register() con error JSON sin code deja code undefined`
- `register() con CHN duplicado propaga status y code`

### `tests/api/samplesClient.spec.ts`

**samplesClient** — 13 pruebas

- `list() retorna items del seed`
- `list() filtra por status`
- `create() crea una muestra nueva`
- `create() con CHN duplicado lanza 409`
- `get() retorna detalle de una muestra existente`
- `get() con id inexistente lanza 404`
- `update() rechaza campo status (RN-04)`
- `process() responde 202 con task_id`
- `sin token, request lanza excepción de tipo ClinicApiException en error de red simulado`
- `softDelete() elimina una muestra existente`
- `softDelete() con muestra VALIDATED lanza 409`
- `getStatus() retorna el estado del pipeline`
- `process() en muestra ya PROCESSING retorna 409`

### `tests/auth/session.spec.tsx`

**useSession** — 3 pruebas

- `lanza error si se usa fuera de SessionProvider`
- `con forceAnalystOnMount, la sesión queda autenticada como analista`
- `logout() limpia la sesión`

**RequireRole** — 2 pruebas

- `sin sesión autenticada, no renderiza los children`
- `renderiza el fallback cuando el rol no coincide`

**authClient.getAccessToken robustez** — 1 prueba

- `retorna null si localStorage lanza excepción`

**SSO (ADR-0020) — sesión leída de un JWT ya presente en localStorage** — 3 pruebas

- `decodifica role y email del JWT sin llamar a authClient.login()`
- `sin token en localStorage, la sesión no está autenticada (sin pedir login propio)`
- `token con formato inválido (no JWT) no autentica`

**renovación automática de la sesión (SSO)** — 5 pruebas

- `renueva el token antes de que expire, sin que el usuario haga nada`
- `si falla la renovación pero al token le queda vida, NO echa al usuario`
- `cuando el token ya caducó y la renovación falla, cierra la sesión`
- `sin token no programa nada: no se llama a la red en la pantalla de login`
- `con un token ya caducado renueva de inmediato, no espera media hora`

### `tests/components/analysisRequestSection.spec.tsx`

**AnalysisRequestSection** — 4 pruebas

- `renderiza los 6 checkboxes`
- `checkbox marcado por defecto se refleja en el estado`
- `marcar un checkbox lo agrega a la selección`
- `desmarcar un checkbox lo quita de la selección`

### `tests/components/chromosomePropertiesPanel.spec.tsx`

**ChromosomePropertiesPanel** — 4 pruebas

- `sin cromosoma muestra el estado vacío`
- `con medidas ausentes muestra los fallbacks "—"`
- `cromosoma rojo (confidence null) muestra "—" y etiqueta de falla`
- `con medidas presentes las muestra`

**ChromosomePropertiesPanel › acciones P3** — 5 pruebas

- `sin callbacks P3 no muestra el bloque de corrección`
- `reclasificar por "Mover a par" dispara onReclassify con la clase destino`
- `separar dispara onSplit`
- `resolver cruce dispara onResolveCross`
- `unir: sin pick previo muestra "marcar"; con pick de otro muestra "confirmar"`

### `tests/components/clinicalHistorySection.spec.tsx`

**ClinicalHistorySection** — 3 pruebas

- `renderiza los 2 textareas`
- `escribir en indicación llama onChange`
- `escribir en antecedentes familiares llama onChange`

### `tests/components/degradedBanner.spec.tsx`

**DegradedBanner** — 3 pruebas

- `renderiza el mensaje de pipeline no disponible`
- `click en Reintentar llama onRetry`
- `click en cerrar llama onDismiss`

### `tests/components/karyoImageToolbar.spec.tsx`

**KaryoImageToolbar (P4)** — 7 pruebas

- `muestra el nivel de zoom`
- `zoom in/out despachan las acciones`
- `rotar izq/der despachan las acciones`
- `el toggle de mover refleja panMode y despacha togglePan`
- `los sliders de brillo/contraste despachan con el valor`
- `reset despacha reset`
- `zoom in deshabilitado al máximo, zoom out al mínimo`

### `tests/components/karyotypeCanvas.spec.tsx`

**KaryotypeCanvas (Konva, P3)** — 8 pruebas

- `renderiza el visor y un botón por cromosoma activo`
- `excluye los cromosomas inactivos (JOIN)`
- `click en un cromosoma dispara onSelect`
- `arrastrar a otro slot dispara onReclassify con la clase destino`
- `soltar en el mismo slot no reclasifica`
- `en modo "Mover" (panMode) el cromosoma no reclasifica al arrastrar`
- `aplica el CSS filter de brillo/contraste al contenedor`
- `con editable=false el cromosoma no es arrastrable (sin onReclassify)`

**KaryotypeCanvas — recorte manual** — 7 pruebas

- `arrastrar emite el bbox del rectángulo`
- `el bbox llega normalizado aunque se arrastre hacia atrás`
- `un clic suelto no dispara un recorte`
- `el rectángulo se ve mientras se arrastra y desaparece al soltar`
- `salir del lienzo cancela el arrastre sin dejar el rectángulo pegado`
- `sin cropMode el arrastre no emite nada`
- `recortando, arrastrar un cromosoma NO lo reclasifica`

### `tests/components/karyotypeViewer.spec.tsx`

**KaryotypeViewer** — 5 pruebas

- `renderiza los cromosomas con su semáforo`
- `renderiza los 24 slots (1–22, X, Y)`
- `click en un cromosoma dispara onSelect con ese cromosoma`
- `el cromosoma seleccionado marca aria-pressed`
- `ordena las copias de un par por position_index`

### `tests/components/metaphaseCaptureSection.spec.tsx`

**MetaphaseCaptureSection** — 15 pruebas

- `muestra "Sin conectar" y placeholder cuando no hay cámara`
- `badge de calidad muestra advertencia con pocas imágenes`
- `badge de calidad muestra "Suficiente" con >=20 imágenes`
- `galería vacía muestra mensaje informativo`
- `galería con imágenes las renderiza`
- `eliminar una imagen individual llama onChange sin esa imagen`
- `limpiar todas pide confirmación y vacía la galería`
- `limpiar todas cancelada no vacía la galería`
- `conectar cámara falla (jsdom) y muestra mensaje de error`
- `subir archivo agrega una imagen a la galería`
- `el botón capturar está deshabilitado sin cámara conectada`
- `cambiar el slider de brillo actualiza el valor mostrado`
- `conectar cámara exitosamente y capturar agrega una imagen`
- `subir múltiples archivos agrega todas las imágenes de una vez (no race condition)`
- `desconectar cámara vuelve al estado inicial`

### `tests/components/patientInfoSection.spec.tsx`

**PatientInfoSection** — 7 pruebas

- `renderiza los 6 campos`
- `escribir en CHN llama onChnChange`
- `escribir en nombre llama onPatientChange con el patch correcto`
- `cambiar género llama onGenderChange`
- `escribir en fecha de nacimiento llama onPatientChange`
- `escribir en documento llama onPatientChange`
- `escribir en teléfono llama onPatientChange`

### `tests/components/processButton.spec.tsx`

**ProcessButton** — 6 pruebas

- `renderiza habilitado cuando status es READY`
- `deshabilitado cuando status es PROCESSING`
- `deshabilitado cuando status es VALIDATED`
- `click encola el procesamiento sin lanzar error ni activar modo degradado`
- `en modo degradado (503 ML_DEGRADED) muestra DegradedBanner`
- `click en Reintentar del DegradedBanner limpia el estado y reintenta`

### `tests/components/registerProcessingModal.spec.tsx`

**RegisterProcessingModal** — 8 pruebas

- `nombra el pipeline REAL, no un modelo que no se construyó`
- `en modo degradado muestra DegradedBanner en vez de la barra de progreso`
- `cuando el status llega a terminal, llama onComplete`
- `con status PROCESSING inicial, hace polling hasta terminar`
- `sin sampleId muestra la barra y el tiempo transcurrido, no un porcentaje del servidor`
- `sin sampleId avisa de no cerrar y no marca ningún paso como completado`
- `sin sampleId no llama a onComplete: todavía no hay nada que abrir`
- `la barra arranca en 0% y nunca miente con un 100% en vuelo`

### `tests/components/sampleDeleteConfirm.spec.tsx`

**SampleDeleteConfirm** — 4 pruebas

- `muestra el CHN de la muestra a eliminar`
- `click en Eliminar llama onConfirm`
- `click en Cancelar llama onCancel`
- `mientras isDeleting=true, el botón muestra estado de carga y está deshabilitado`

### `tests/components/sampleFilters.spec.tsx`

**SampleFilters** — 6 pruebas

- `click en un filter-chip de estado llama onChange`
- `volver a "Todas" limpia el filtro de status`
- `el chip activo refleja el filtro actual`
- `cambiar fecha desde llama onChange`
- `cambiar fecha hasta llama onChange`
- `escribir en búsqueda CHN dispara onChange tras el debounce`

### `tests/components/sampleFormModal.spec.tsx`

**SampleFormModal** — 5 pruebas

- `modo create: renderiza campos vacíos`
- `modo create: submit vacío muestra errores de validación`
- `modo create: submit válido llama onSubmit con los datos`
- `modo edit: campo CHN está deshabilitado (RN-04)`
- `click en Cancelar llama onCancel`

### `tests/components/sampleInfoSection.spec.tsx`

**SampleInfoSection** — 7 pruebas

- `muestra el código autogenerado como readonly`
- `cambiar tipo de muestra llama onChange`
- `escribir médico solicitante llama onChange`
- `cambiar fecha de recolección llama onChange`
- `cambiar fecha de recepción llama onChange`
- `cambiar método de cultivo llama onChange`
- `escribir departamento llama onChange`

### `tests/components/samplePagination.spec.tsx`

**SamplePagination** — 6 pruebas

- `muestra el rango y total correctos`
- `botón Siguiente llama onPageChange con page+1`
- `botón Anterior llama onPageChange con page-1`
- `botón Anterior está deshabilitado en la primera página`
- `botón Siguiente está deshabilitado en la última página`
- `con total=0, muestra rango 0-0`

### `tests/components/sampleTable.spec.tsx`

**SampleTable** — 6 pruebas

- `renderiza las filas con CHN y estado`
- `muestra estado vacío cuando no hay items`
- `click en Editar llama onEdit con el id correcto`
- `analista (rol por defecto en forceAnalystOnMount) NO ve botón Eliminar (RN-06 gating)`
- `el link de CHN apunta al detalle de la muestra`
- `muestra el nombre del analista`

### `tests/components/statusPoller.spec.tsx`

**StatusPoller** — 4 pruebas

- `renderiza el track de estados`
- `no hace polling si el estado inicial ya es terminal (READY)`
- `no hace polling si el estado inicial es VALIDATED`
- `con status inicial PROCESSING, hace polling y muestra el resultado con chromosome_count`

### `tests/components/supervisorAuditPanel.spec.tsx`

**SupervisorAuditPanel (S1)** — 3 pruebas

- `lista la selección del 5% con badges y contador`
- `confirmar un cromosoma sube el contador y bloquea sus acciones`
- `rechazar con comentario refleja la decisión`

**SupervisorAuditPanel (S1) › firma MFA** — 4 pruebas

- `el botón Firmar se habilita al completar la auditoría`
- `firmar con MFA correcto (123456) marca el caso como firmado`
- `MFA inválido muestra el error en el modal`
- `con el caso firmado muestra el banner de firmado`

### `tests/components/supervisorIscnPanel.spec.tsx`

**SupervisorIscnPanel (S3) › generación del ISCN** — 3 pruebas

- `ofrece generar cuando el caso está firmado y aún no tiene nomenclatura`
- `genera la nomenclatura y la muestra como read-only`
- `muestra el ISCN ya persistido sin volver a generarlo`

**SupervisorIscnPanel (S3) › override justificado (RN-04)** — 4 pruebas

- `exige nomenclatura Y justificación antes de habilitar el envío`
- `aplica el override y lo marca como tal`
- `muestra el error del backend si la gramática es inválida`
- `cancelar cierra el formulario sin cambiar nada`

**SupervisorIscnPanel (S3) › narrativa asistida (ADR-0024)** — 5 pruebas

- `el borrador se marca como tal y exige revisión`
- `muestra los campos tipados, no solo la prosa`
- `un cariotipo normal se distingue de uno con alteraciones`
- `deja ver qué modelo la redactó y sobre qué ISCN`
- `sin ISCN no ofrece redactar: no hay dato clínico que narrar`

### `tests/components/toast.spec.tsx`

**Toast** — 4 pruebas

- `renderiza el mensaje`
- `click en cerrar llama onDismiss`
- `se autodescarta después de autoDismissMs`
- `aplica data-kind según el tipo`

### `tests/hooks/useCamera.spec.ts`

**useCamera** — 9 pruebas

- `estado inicial: desconectado, sin error`
- `connect() exitoso marca isConnected=true`
- `connect() rechazado por el usuario setea error`
- `disconnect() detiene el stream y marca isConnected=false`
- `capture() sin cámara conectada retorna null`
- `connect() asigna srcObject al elemento video cuando videoRef está attacheado`
- `capture() con cámara conectada y video attacheado retorna dataURL`
- `capture() cuando getContext retorna null, retorna null`
- `disconnect() limpia srcObject del video attacheado`

### `tests/hooks/useDegradedMode.spec.tsx`

**useDegradedMode (P4)** — 2 pruebas

- `con IA disponible reporta degraded=false y modo auto`
- `con IA caída reporta degraded=true y propaga modo degradado al cliente`

### `tests/hooks/useSampleMutations.spec.tsx`

**useSampleMutations** — 3 pruebas

- `useCreateSample crea una muestra`
- `useUpdateSample actualiza patient_ref`
- `useDeleteSample elimina una muestra`

### `tests/lib/historial.spec.ts`

**deshacer y rehacer** — 4 pruebas

- `deshacer devuelve al estado anterior`
- `rehacer vuelve a aplicar lo deshecho`
- `una acción nueva invalida el rehacer`
- `deshacer sin historial no rompe ni cambia nada`

**fusión de acciones consecutivas** — 2 pruebas

- `arrastrar un deslizador deja UN solo punto de retorno`
- `la fusión se corta si entre medias hay otra acción`

**acciones ignoradas** — 1 prueba

- `no crean punto de retorno pero sí cambian el estado`

**higiene del historial** — 2 pruebas

- `una acción que no cambia el estado no apila nada`
- `el historial no crece sin límite`

**atajo de teclado** — 6 pruebas

- `Ctrl+Z deshace`
- `Ctrl+Shift+Z rehace`
- `Ctrl+Y rehace (convención Windows)`
- `Cmd+Z funciona en Mac`
- `la Z sola no hace nada`
- `dentro de un campo de texto NO se roba el Ctrl+Z del navegador`

### `tests/lib/karyoLayout.spec.ts`

**karyoLayout — geometría pura del cariograma (DD-KARYO-003)** — 10 pruebas

- `slotOrigin ubica el slot 1 en la esquina y avanza por columnas`
- `slotOrigin baja a la segunda fila en el slot 13 (índice 12)`
- `slotOrigin devuelve null para un slot inexistente`
- `chromosomePosition desplaza por position_index (copia)`
- `chromosomePosition cae en el pad si la clase es inválida`
- `slotAtPoint invierte slotOrigin (centro del slot 1 → "1")`
- `slotAtPoint devuelve null fuera de la grilla`
- `reclassifyTargetFromDrop retorna la clase destino cuando cambia de slot`
- `reclassifyTargetFromDrop retorna null si cae en el mismo slot`
- `reclassifyTargetFromDrop retorna null si cae fuera de la grilla`

### `tests/lib/medicion.spec.ts`

**distancia** — 2 pruebas

- `mide la hipotenusa entre dos puntos`
- `es cero entre un punto y sí mismo`

**medirCromosoma — morfologías reales** — 4 pruebas

- `brazos iguales dan metacéntrico (como el cromosoma 1)`
- `centrómero desplazado da submetacéntrico (como el 4 o el 5)`
- `centrómero muy cerca del extremo da acrocéntrico (como el 13, 14, 15, 21, 22)`
- `sin brazo corto apreciable da telocéntrico`

**medirCromosoma — invariantes** — 4 pruebas

- `p es el brazo corto aunque el analista marque los extremos al revés`
- `el índice centromérico nunca supera 50`
- `mide en diagonal igual que en vertical`
- `un cromosoma sin longitud no revienta ni inventa morfología`

**morfologiaPorIndice — los cortes de Levan** — 8 pruebas

- `IC 50% → metacéntrico`
- `IC 37.5% → metacéntrico`
- `IC 37.4% → submetacéntrico`
- `IC 25% → submetacéntrico`
- `IC 24.9% → acrocéntrico`
- `IC 12.5% → acrocéntrico`
- `IC 12.4% → telocéntrico`
- `IC 0% → telocéntrico`

**longitudRelativa** — 2 pruebas

- `expresa el tamaño como porcentaje del total medido`
- `sin total no divide por cero`

**resumenMedida** — 2 pruebas

- `da las tres cifras en el orden en que se leen`
- `muestra ∞ en vez de romperse cuando no hay brazo corto`

### `tests/lib/recorte.spec.ts`

**rectanguloDeRecorte** — 4 pruebas

- `arrastrando hacia abajo y a la derecha`
- `arrastrando hacia arriba y a la izquierda da el MISMO rectángulo`
- `mezclando direcciones (arriba-derecha)`
- `redondea: el bbox se mide en píxeles enteros`

**esRecorteUtil** — 3 pruebas

- `un clic sin arrastre no es un recorte`
- `una franja finísima tampoco: no cabe un cromosoma`
- `un rectángulo del tamaño mínimo sí vale`

### `tests/lib/viewport.spec.ts`

**viewport — reducer puro de herramientas de imagen (DD-KARYO-004)** — 9 pruebas

- `zoomIn/zoomOut cambian la escala en pasos`
- `zoom respeta los límites [SCALE_MIN, SCALE_MAX]`
- `rotateLeft/rotateRight normalizan el ángulo a [0,360)`
- `setBrightness/setContrast se acotan a [50,150]`
- `pan acumula el offset`
- `togglePan alterna el modo mover`
- `reset vuelve al estado inicial`
- `acción desconocida devuelve el mismo estado`
- `zoomPercent y cssFilter formatean correctamente`

**voltear — transformación de vista** — 5 pruebas

- `el espejo horizontal alterna y no toca el resto del estado`
- `voltear dos veces vuelve al original`
- `stageScale devuelve escala con signo sin perder el zoom`
- `sin voltear, stageScale es la escala tal cual`
- `restablecer deshace también el volteo`

### `tests/msw/karyotypeSeed.spec.ts`

**karyotypeSeed — metafases MetaClass reconstruidas** — 5 pruebas

- `caso genérico (no MetaClass) = 46 cromosomas con 3 naranjas`
- `46,XX normal: 46 cromosomas, dos X, sin naranjas`
- `47,XY,+21 (Down): 47 cromosomas, tres copias del 21 (una anómala naranja)`
- `47,XXY (Klinefelter): 47 cromosomas, dos X + una Y, X extra anómala`
- `META_CASES declara los 3 ISCN esperados`

### `tests/mswBootstrap.spec.tsx`

**Infraestructura MSW — frontend-clinic** — 4 pruebas

- `public/mockServiceWorker.js existe y no está vacío`
- `package.json declara msw.workerDirectory apuntando a public/`
- `vite.config.ts define el proxy condicional a VITE_USE_MSW`
- `main.tsx invoca worker.start() condicionado a USE_MSW antes de montar React`

### `tests/pages/degradedModePage.spec.tsx`

**DegradedModePage** — 3 pruebas

- `renderiza el encabezado de modo degradado`
- `lista las instrucciones de análisis manual`
- `tiene un link de vuelta a la lista de muestras`

### `tests/pages/karyotypeP2.spec.tsx`

**KaryotypePage — P2 (XAI + resolución + gating + audit)** — 7 pruebas

- `seleccionar un naranja muestra acciones; Aceptar deshabilitado hasta ver XAI`
- `ver XAI abre el modal con heatmap y habilita Aceptar`
- `resolver un naranja baja la cuenta de revisión`
- `botón Pasar a Supervisor bloqueado hasta resolver todos los naranjas`
- `marcar anomalía refleja el estado en el panel`
- `si el XAI falla, el modal muestra el error`
- `la bitácora de auditoría registra las acciones`

### `tests/pages/karyotypeP3.spec.tsx`

**KaryotypePage — P3 (corrección manual sobre Konva)** — 6 pruebas

- `reclasificar con "Mover a par" resuelve el naranja y baja la cuenta de revisión`
- `reclasificar por drag & drop a otro par resuelve el naranja`
- `separar (touching) agrega un cromosoma al visor`
- `unir dos fragmentos deja uno inactivo (desaparece del visor)`
- `resolver cruce marca el naranja como resuelto (baja la cuenta)`
- `la bitácora registra la reclasificación (CORRECT_CLASS)`

### `tests/pages/karyotypeP4.spec.tsx`

**KaryotypePage — P4 (herramientas de imagen + modo degradado)** — 4 pruebas

- `la toolbar de imagen ajusta el zoom y restablece`
- `el brillo aplica un CSS filter al lienzo`
- `con la IA caída muestra el banner de Modo Manual`
- `en modo degradado, una corrección manual queda marcada "degradado" en la bitácora`

### `tests/pages/karyotypePage.spec.tsx`

**KaryotypePage** — 7 pruebas

- `muestra skeleton mientras carga`
- `renderiza el visor con 46 cromosomas y la leyenda`
- `muestra el banner de revisión con la cuenta de naranjas`
- `seleccionar un cromosoma muestra sus propiedades`
- `muestra_mensaje NO_KARYOTYPE para muestra sin cariotipo`
- `muestra banner rojo cuando hay cromosomas con clasificación fallida`
- `error genérico (no NO_KARYOTYPE) muestra mensaje de fallo de carga`

### `tests/pages/karyotypeRecorte.spec.tsx`

**KaryotypePage — recorte manual** — 5 pruebas

- `recortar cambia la clase del cromosoma`
- `tras recortar hay que volver a mirar el XAI antes de aceptar (BR-004)`
- `el modo se apaga solo al soltar`
- `queda registrado en la bitácora`
- `medir y recortar no se pisan`

### `tests/pages/karyotypeSupervisor.spec.tsx`

**KaryotypePage — Supervisor S1 (gating del panel de auditoría)** — 4 pruebas

- `supervisor sobre caso ANALYST_VALIDATED ve el panel de auditoría 5%`
- `analista NO ve el panel de auditoría (segregación de funciones)`
- `supervisor sobre caso READY (aún no validado) no ve el panel`
- `supervisor sobre caso SIGNED ve el banner de reporte firmado (S2)`

### `tests/pages/sampleDetailPage.spec.tsx`

**SampleDetailPage** — 6 pruebas

- `muestra skeleton mientras carga`
- `renderiza el CHN y estado tras cargar`
- `muestra la metadata de la muestra`
- `id inexistente muestra mensaje de error`
- `click en Editar navega a la página de edición`
- `link "Ver cariotipo" apunta a la ruta React del visor (ADR-0021 P1)`

### `tests/pages/sampleFormPage.spec.tsx`

**SampleFormPage** — 5 pruebas

- `modo create: renderiza el modal de nueva muestra`
- `modo create: crear una muestra navega de vuelta a la lista`
- `modo edit: carga los datos existentes de la muestra`
- `click en Cancelar navega de vuelta a la lista`
- `modo edit: guardar cambios navega de vuelta a la lista`

### `tests/pages/sampleListPage.spec.tsx`

**SampleListPage** — 10 pruebas

- `renderiza las muestras del seed tras cargar`
- `las stat cards reflejan los conteos por estado`
- `búsqueda sin coincidencias muestra el empty-state`
- `filtro por status VALIDATED reduce el listado`
- `búsqueda por CHN filtra con debounce`
- `click en Nueva Muestra navega al formulario (verificado por presencia del botón)`
- `click en Eliminar (rol admin no aplica en analista) no muestra confirm porque el botón está oculto`
- `rol admin: flujo completo de eliminar muestra funciona`
- `rol admin: cancelar el modal de eliminar lo cierra sin borrar`
- `paginación: cambiar de página actualiza los items mostrados`

### `tests/pages/sampleRegisterPage.spec.tsx`

**SampleRegisterPage** — 12 pruebas

- `renderiza las 5 secciones del formulario`
- `el código de muestra se autogenera con formato BM-`
- `guardar borrador sin CHN muestra error`
- `guardar borrador con solo CHN funciona`
- `registrar sin CHN ni nombre muestra error`
- `registrar con menos de 3 imágenes muestra error`
- `registro completo exitoso abre el modal de procesamiento`
- `registro completo: al terminar el polling navega al visor de cariotipo (P1-P4)`
- `registro con CHN duplicado muestra error del backend`
- `cancelar con confirmación navega a la lista`
- `cancelar sin confirmar no navega`
- `marcar un análisis adicional actualiza el estado`

### `tests/pages/supervisorInboxPage.spec.tsx`

**SupervisorInboxPage › agrupación por etapa del flujo** — 5 pruebas

- `muestra las tres etapas del Supervisor`
- `coloca cada caso en la etapa que le corresponde`
- `cuenta los casos por etapa`
- `resume cuántos casos esperan acción (validados + firmados)`
- `una etapa sin casos lo dice, en vez de quedar vacía`

**SupervisorInboxPage › acción por etapa** — 2 pruebas

- `la acción ofrecida depende del estado del caso`
- `abrir un caso lleva al visor, donde vive el gating real`

**SupervisorInboxPage › segregación de roles (RN-06)** — 2 pruebas

- `el analista no ve la bandeja`
- `el admin sí la ve`

### `tests/pages/toolQueryPage.spec.tsx`

**ToolQueryPage — escenario 1: controlado** — 3 pruebas

- `resuelve sin modelo y lo dice en pantalla`
- `muestra la herramienta y la tabla de origen`
- `renderiza los datos como tabla`

**ToolQueryPage — escenario 2: sinónimo** — 3 pruebas

- `el modelo elige la herramienta y se marca el camino LLM`
- `expone por qué el modelo eligió esa herramienta`
- `devuelve los mismos datos que el escenario 1`

**ToolQueryPage — escenario 3: fuera de alcance** — 3 pruebas

- `dice que no sabe sin mostrar un error`
- `no inventa datos`
- `publica qué SÍ puede responder`

**ToolQueryPage — escenario 4: modelo apagado** — 2 pruebas

- `los datos siguen saliendo correctos`
- `el sinónimo deja de funcionar — eso es lo que aporta la IA`

**ToolQueryPage — usabilidad** — 4 pruebas

- `publica el catálogo antes de preguntar`
- `los escenarios precargados disparan la consulta`
- `no consulta con el campo vacío`
- `muestra la latencia de cada consulta`

---

## 6 · `frontend-admin` — 220 unit tests

### `tests/adminClient.spec.ts`

**adminClient › list()** — 8 pruebas

- `devuelve solo usuarios activos`
- `mapea 401 → AdminApiError unauthorized`
- `mapea 403 → AdminApiError forbidden`
- `mapea 500 → AdminApiError server`
- `mapea 502 → AdminApiError server`
- `mapea 418 → AdminApiError unknown`
- `mapea 401 sin detail → mensaje por defecto`
- `mapea 400 con fieldErrors tipo string`

**adminClient › get(id)** — 3 pruebas

- `devuelve un usuario por id`
- `mapea 404 → AdminApiError not_found`
- `mapea 404 con cuerpo no-JSON → unknown`

**adminClient › create(draft)** — 3 pruebas

- `crea un usuario y devuelve 201`
- `mapea 409 email duplicado → conflict`
- `mapea 400 validación → validation con fieldErrors`

**adminClient › update(id, patch)** — 2 pruebas

- `actualiza full_name y role`
- `mapea 403 → forbidden`

**adminClient › softDelete(id)** — 1 prueba

- `soft-delete devuelve 204`

**adminClient › history(id)** — 3 pruebas

- `devuelve entradas de auditoría`
- `devuelve array vacío cuando no hay entradas`
- `pasa query params a la URL (cubre buildUrl)`

**adminClient › exchangeFastApiJwt()** — 2 pruebas

- `canjea JWT y guarda token`
- `mapea 400 → validation`

**adminClient › network errors** — 1 prueba

- `mapea fallo de fetch → AdminApiError network`

**adminClient › auth token** — 6 pruebas

- `envía Authorization Token header cuando solo hay token de exchange F0 (sin sesión)`
- `prioriza el JWT de sesión (login unificado ADR-0017) sobre el token de exchange F0`
- `sin token de exchange F0 ni sesión, no envía Authorization`
- `logout limpia el token`
- `getAuthToken retorna null si localStorage lanza`
- `setAuthToken no lanza si localStorage falla`

**adminClient › buildUrl — query string** — 1 prueba

- `omite query params con value vacío/null/undefined`

**adminClient › buildUrl helper — query string** — 1 prueba

- `incluye solo params con valor definido`

### `tests/adminConfigClient.spec.ts`

**adminConfigClient** — 17 pruebas

- `envía Bearer con el JWT de sesión (login unificado ADR-0017), no requiere token de exchange F0`
- `getProfile devuelve el payload del MSW`
- `updateProfile envía PATCH y devuelve el perfil actualizado`
- `mapea 400 con fieldErrors a error kind=validation`
- `400 con fieldError como string (no array) se mapea a [string]`
- `mapea 401 a kind=unauthorized`
- `mapea 403 a kind=forbidden`
- `mapea 404 a kind=not_found`
- `mapea 409 a kind=conflict`
- `mapea 5xx a kind=server`
- `status no manejado (ej. 418) → kind=unknown`
- `204 se maneja en request() — verificamos la rama via respuesta vacía del MSW`
- `payload no-JSON se convierte a { detail: text }`
- `fetch que lanza (network) → kind=network`
- `respuesta vacía sin content`
- `safeReadToken — localStorage.getItem que lanza (modo privado) → request sin Authorization funciona`
- `401/403/404/409 con payload {} (sin detail) → usa mensaje por defecto`

### `tests/adminUsersStore.spec.tsx`

**adminUsersStore (puro, con client inyectado)** — 10 pruebas

- `lanza error si useAdminUsers se usa fuera del provider`
- `load() exitoso actualiza state.users`
- `load() con error → state.status=error y message`
- `createUser() inserta en users`
- `updateUser() reemplaza existente por id`
- `deleteUser() quita de users`
- `openHistory() y closeHistory()`
- `openHistory() con error → historyStatus=error`
- `load() con throw que no es Error → mensaje por defecto`
- `createUser() inserta o reemplaza (upsert por id)`

### `tests/auth/authClient.spec.ts`

**authClient (ADR-0017)** — 11 pruebas

- `isAuthenticated es false sin tokens`
- `login exitoso guarda tokens y devuelve role/email/full_name`
- `login con credenciales inválidas lanza AuthApiException y no guarda tokens`
- `me() sin token devuelve null sin hacer fetch`
- `me() con token válido devuelve los datos del usuario`
- `refresh() sin refresh token devuelve null`
- `refresh() con token válido devuelve un nuevo access y lo persiste`
- `logout limpia los tokens locales`
- `refresh() tras logout falla y limpia tokens (blacklist real vía MSW)`
- `decodeExp lee el claim exp de un JWT válido`
- `decodeExp devuelve null para un token malformado`

### `tests/auth/authContext.spec.tsx`

**AuthContext (ADR-0017)** — 6 pruebas

- `sin tokens en localStorage: isLoading termina en false, no autenticado`
- `login exitoso actualiza user y authenticated`
- `login fallido no autentica y propaga el error`
- `logout limpia user y authenticated`
- `hidrata la sesión al montar si ya hay un access token válido en localStorage`
- `useAuth fuera de AuthProvider lanza`

### `tests/auth/privateRoute.spec.tsx`

**PrivateRoute (ADR-0017)** — 4 pruebas

- `sin sesión redirige a /login`
- `con sesión y rol permitido renderiza el contenido protegido`
- `con sesión pero rol no permitido (con destino externo) navega fuera vía roleRedirect`
- `con sesión pero rol no permitido sin destino externo (admin) redirige a /login`

### `tests/auth/roleRedirect.spec.ts`

**getRedirectForRole (ADR-0017 D7)** — 4 pruebas

- `admin devuelve null (se queda en la SPA)`
- `analista devuelve la URL de frontend-clinic /clinic/samples`
- `supervisor devuelve el destino externo configurado`
- `solo admin se queda en esta SPA; los otros dos navegan fuera`

### `tests/components/adminUsersPanel.spec.tsx`

**AdminUsersPanel — integración con MSW** — 4 pruebas

- `carga la lista y muestra usuarios activos`
- `abre el formulario al click en "Nuevo usuario"`
- `cierra el formulario al cancelar`
- `crea un usuario y aparece en la tabla`

### `tests/components/appearanceSection.spec.tsx`

**AppearanceSection — P6** — 9 pruebas

- `muestra loading inicial y luego los 4 selects con defaults del MSW`
- `aplica data-theme y lang en <html> al montar`
- `cambiar tema y guardar hace PATCH solo con ese campo y reaplica data-theme`
- `cancelar revierte ediciones no guardadas`
- `cambiar idioma y tamaño de fuente hace PATCH con ambos campos`
- `guardar sin cambios no llama al backend pero da feedback`
- `error de validación (400) → banner con el campo señalado`
- `error del backend con detail plano (sin fieldErrors) → usa err.error.message`
- `error de carga inicial → banner con Reintentar`

### `tests/components/atoms.spec.tsx`

**RoleBadge** — 3 pruebas

- `renderiza etiqueta de analista`
- `renderiza etiqueta de supervisor`
- `renderiza etiqueta de administrador`

**StatusToggle** — 4 pruebas

- `muestra "Activo" cuando active=true`
- `muestra "Inactivo" cuando active=false`
- `llama onChange al cambiar`
- `respeta disabled`

**EmptyState** — 1 prueba

- `renderiza título y hint`

### `tests/components/biomedShell.spec.tsx`

**useSession — localStorage helpers** — 3 pruebas

- `getStoredRole devuelve null cuando no hay rol guardado`
- `setStoredRole persiste y getStoredRole lee`
- `setStoredRole(null) limpia el valor`

**SessionProvider** — 3 pruebas

- `expone isAdmin=true cuando role=admin`
- `expone isAdmin=false cuando role=supervisor`
- `forceAdminOnMount=true fuerza role=admin cuando no hay rol`

**BiomedSidebar — gating por rol** — 4 pruebas

- `muestra 6 secciones y oculta "Usuarios" cuando role≠admin`
- `muestra "Usuarios" cuando role=admin`
- `marca la sección activa con aria-current=page`
- `invoca onSelect al click en un item`

**BiomedShell — layout institucional** — 7 pruebas

- `renderiza navbar + sidebar + contenido`
- `cambia de sección al hacer click en un item del sidebar`
- `cae a profile si la sección activa requiere admin y role≠admin`
- `muestra navbar con brand BIOMED UMSS`
- `monta AdminUsersProvider + AdminUsersPanel dentro de la sección "users"`
- `muestra el botón "Salir" (ADR-0017, replica configuracion.html nav-item)`
- `click en "Salir" llama logout y navega a /login`

### `tests/components/configForm.spec.tsx`

**ConfigForm — genérico** — 8 pruebas

- `hidrata los inputs desde `initial``
- `muestra error de validación Zod en el campo correspondiente`
- `envía solo los campos modificados en el diff`
- `muestra banner general con mensaje de Error si onSubmit lanza`
- `muestra banner general "Error al guardar" si onSubmit lanza con string`
- `submit sin cambios (diff vacío) → no llama onSubmit y muestra "Guardado a las …"`
- `rehidrata el formulario cuando `initial` cambia (refresh)`
- `muestra botón Cancelar y llama onCancel al hacer click`

### `tests/components/configSection.spec.tsx`

**ConfigSection — esqueleto loading/error/data** — 4 pruebas

- `muestra loading y luego el children con los datos`
- `muestra banner de error + botón Reintentar si load() lanza`
- `Reintentar vuelve a llamar load()`
- `refresh() expuesto al children re-dispara load()`

### `tests/components/coverageBoost.spec.tsx`

**AdminUsersPanel — flujos secundarios (cobertura)** — 11 pruebas

- `muestra error si load() falla`
- `muestra empty state cuando la lista viene vacía`
- `abre dialog de edit y guarda cambios`
- `abre dialog de delete y cancela`
- `abre dialog de delete y confirma eliminación`
- `abre historial y muestra entradas`
- `botón recargar invoca load() de nuevo`
- `muestra dialog-error si createUser lanza`
- `muestra dialog-error si deleteUser lanza`
- `muestra modal de historial con lista vacía`
- `muestra "No se pudo cargar el historial" cuando history falla`

**UserTable — handlers** — 1 prueba

- `invoca onEdit, onDelete, onShowHistory`

**UserDeleteConfirm** — 2 pruebas

- `muestra info y llama onConfirm / onCancel`
- `respeta busy (botón disabled)`

**UserTable — branches** — 1 prueba

- `muestra status "Inactivo" para usuarios no activos`

### `tests/components/modelsSection.spec.tsx`

**ModelsSection — P3** — 13 pruebas

- `muestra loading inicial y luego el contenido con datos reales del MSW`
- `carga métricas reales: última métrica + sparkline con 3 snapshots`
- `estado vacío de métricas cuando no hay snapshots`
- `error al cargar métricas no bloquea el formulario de configuración`
- `banner de cumplimiento visible cuando confidence_threshold < 0.85`
- `cambiar el slider y guardar hace PATCH y refleja compliance_warning`
- `cambiar el slider de sensibilidad hace PATCH con el nuevo valor`
- `guardar sin cambios no llama al backend pero da feedback`
- `restaurar valores por defecto revierte ediciones no guardadas`
- `cambiar analysis_mode y log_level hace PATCH con los nuevos valores`
- `toggle de U-Net/EfficientNet cambia estado local y se guarda en PATCH`
- `PATCH invalido (analysis_mode fuera de choices) muestra error general`
- `error de carga inicial del config → banner con Reintentar`

### `tests/components/notificationsSection.spec.tsx`

**NotificationsSection — P4** — 8 pruebas

- `muestra loading inicial y luego la matriz + horario silencioso`
- `togglear una celda y guardar hace PATCH solo con ese campo`
- `activar horario silencioso revela los time pickers y permite cambiarlos`
- `error de validación con fieldErrors → banner aplanado por campo`
- `cancelar revierte ediciones no guardadas`
- `guardar sin cambios no llama al backend pero da feedback`
- `error del backend en PATCH → banner general`
- `error de carga inicial → banner con Reintentar`

### `tests/components/profileSection.spec.tsx`

**ProfileSection — P1** — 14 pruebas

- `muestra loading inicial y luego el header + form con datos del MSW`
- `muestra error de validación Zod si full_name tiene <3 caracteres`
- `muestra error de validación si email no tiene formato`
- `PATCH válido → muestra feedback "Guardado a las …"`
- `error del backend → banner general con mensaje del fieldError`
- `error de carga inicial → muestra banner con botón Reintentar`
- `tras PATCH el header se actualiza con el nuevo full_name`
- `error de red en PATCH → banner general con mensaje del AdminApiException`
- `error con detail plano (sin fieldErrors) → muestra el detail en el banner`
- `AdminApiException con kind=validation pero fieldErrors vacío → usa err.message`
- `error que no es Error ni AdminApiException → mensaje "Error desconocido"`
- `header omite specialty y license cuando están vacíos`
- `header muestra specialty y license cuando están definidos`
- `error de validación con fieldErrors de arrays vacíos → usa err.error.message`

### `tests/components/securitySection.spec.tsx`

**SecuritySection — P2** — 1 prueba

- `muestra loading inicial y luego ambos bloques (password + 2FA)`

**SecuritySection — P2 › Cambiar contraseña** — 4 pruebas

- `valida contraseña muy corta antes de llamar al backend`
- `valida mismatch entre nueva y confirmación`
- `submit válido → feedback "Contraseña actualizada a las …"`
- `current incorrecta → banner de error del backend`

**SecuritySection — P2 › 2FA** — 6 pruebas

- `activar: click en toggle → genera QR/secret → código inválido rechazado`
- `activar: código válido → 2FA queda habilitado`
- `código con formato inválido (no 6 dígitos) se rechaza client-side`
- `cancelar durante el setup vuelve al estado inicial (sin QR)`
- `desactivar: 2FA ya habilitado → click pide código directo (sin QR nuevo)`
- `error del backend en /2fa/setup/ → banner general`

### `tests/components/userForm.spec.tsx`

**UserForm — validación** — 10 pruebas

- `muestra error si nombre <2 caracteres`
- `muestra error si email vacío en modo creación`
- `muestra error si email no tiene formato`
- `muestra error si la contraseña es débil (corta)`
- `muestra error si la contraseña no coincide con la confirmación`
- `llama onSubmit con draft válido (incluye password)`
- `email es readOnly en modo edición y no muestra campos de password`
- `llama onCancel al click en cancelar`
- `muestra error general si onSubmit lanza`
- `muestra error general "Error al guardar" si onSubmit lanza con string`

### `tests/mswBootstrap.spec.tsx`

**SPEC-007 — MSW bootstrap (mock no intercepta) › MswBootstrapError component** — 5 pruebas

- `renderiza el banner de error con un mensaje claro cuando MSW falla`
- `muestra el hint de regeneración cuando el error contiene palabras clave de "not found"`
- `serializa errores que no son instancias de Error sin crashear`
- `invoca onRetry cuando el usuario hace clic en "Reintentar"`
- `expone un link a la doc oficial de MSW`

**SPEC-007 — MSW bootstrap (mock no intercepta) › Infraestructura — mockServiceWorker.js presente** — 2 pruebas

- `public/mockServiceWorker.js existe y no está vacío`
- `package.json declara msw.workerDirectory apuntando a public/`

**SPEC-007 — MSW bootstrap (mock no intercepta) › vite.config.ts — proxy condicional a VITE_USE_MSW** — 1 prueba

- `define el proxy dentro de un ternario que evalúa useMsw`

### `tests/pages/loginPage.spec.tsx`

**LoginPage (ADR-0017, replica index.html #loginModal)** — 8 pruebas

- `renderiza el header, los 3 tabs de rol y el formulario`
- `el banner de error no se muestra antes de un intento fallido`
- `el tab "citogenetista" está seleccionado por defecto`
- `click en un tab lo marca como seleccionado (cosmético, ADR-0017 D8)`
- `login exitoso como admin navega a la raíz de la SPA (no cross-app)`
- `login exitoso como analista navega fuera vía window.location.href (D8: tab elegido no importa)`
- `credenciales inválidas muestran el banner de error y no navegan`
- `el botón muestra "Ingresando…" mientras se envía`

