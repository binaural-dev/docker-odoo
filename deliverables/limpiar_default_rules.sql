-- Borra el clon "Default Structure Rules Set" que sembraba
-- binaural_hr_payroll_standard_data. No toca la estructura del core Odoo
-- (hr_payroll.default_structure), solo los xmlid del módulo standard.
BEGIN;
DELETE FROM hr_salary_rule WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'binaural_hr_payroll_standard_data'
      AND model  = 'hr.salary.rule'
      AND name LIKE 'rule_default_rules%');
DELETE FROM hr_payroll_structure WHERE id IN (
    SELECT res_id FROM ir_model_data
    WHERE module = 'binaural_hr_payroll_standard_data'
      AND model  = 'hr.payroll.structure'
      AND name = 'structure_default_rules');
DELETE FROM ir_model_data
 WHERE module = 'binaural_hr_payroll_standard_data'
   AND name LIKE '%default_rules%';
COMMIT;
