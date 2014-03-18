---
--- avrc_data/value_integer -> pirc/value_integer + pirc/value_choice
---


CREATE FOREIGN TABLE value_integer_ext (
    id              SERIAL NOT NULL

  , entity_id       INTEGER NOT NULL
  , attribute_id    INTEGER NOT NULL
  , value           INTEGER NOT NULL

  , create_date     DATETIME NOT NULL
  , create_user_id  INTEGER NOT NULL
  , modify_date     DATETIME NOT NULL
  , modify_user_id  INTEGER NOT NULL
  , revision        INTEGER NOT NULL
)
SERVER trigger_target
OPTIONS (table_name 'value_integer');


--
-- Helper function to find the value_integer id in the new system using
-- the old system id number
--
CREATE OR REPLACE FUNCTION ext_value_integer_id(id) RETURNS SETOF integer AS $$
  BEGIN
    RETURN QUERY
        SELECT id
        FROM "value_integer_ext"
        WHERE (entity_id, attribute_id, value) = (
          SELECT ext_entity_id(entity_id)
                ,ext_attribute_id(attribute_id)
                ,value
          FROM "integer"
          WHERE id = $1)
  END;
$$ LANGUAGE plpgsql;


--
-- Helper function to find the value_choice id in the new system using
-- the old system id number in the integer table
--
CREATE OR REPLACE FUNCTION ext_integer_value_choice_id(id) RETURNS SETOF integer AS $$
  BEGIN
    RETURN QUERY
        SELECT id
        FROM "value_choice_ext"
        WHERE (entity_id, attribute_id, value) = (
          SELECT ext_entity_id(entity_id)
                ,ext_attribute_id(attribute_id)
                ,ext_choice_id(choice_id)
          FROM "integer"
          WHERE id = $1)
  END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION value_integer_mirror() RETURNS TRIGGER AS $value_integer_mirror$
  BEGIN
    CASE TG_OP
      WHEN 'INSERT' THEN

        IF NEW.value IS NOT NULL THEN
          IF NEW.choice_id IS NULL THEN
            INSERT INTO value_integer_ext (
                entity_id
              , attribute_id
              , value
              , create_date
              , create_user_id
              , modify_date
              , modify_user_id
              , revision)
            VALUES (
                ext_user_id(NEW.entity_id)
              , ext_attribute_id(NEW.attribute_id)
              , NEW.value
              , NEW.create_date
              , ext_user_id(NEW.create_user_id)
              , NEW.modify_date
              , ext_user_id(NEW.modify_user_id)
              , NEW.revision
              );
          ELSE
             INSERT INTO value_choice_ext (
                entity_id
              , attribute_id
              , value
              , create_date
              , create_user_id
              , modify_date
              , modify_user_id
              , revision)
            VALUES (
                ext_user_id(NEW.entity_id)
              , ext_attribute_id(NEW.attribute_id)
              , ext_choice_id(NEW.choice_id)
              , NEW.create_date
              , ext_user_id(NEW.create_user_id)
              , NEW.modify_date
              , ext_user_id(NEW.modify_user_id)
              , NEW.revision
              );
          END IF;
        END IF;

      WHEN 'DELETE' THEN
        IF OLD.choice_id IS NULL THEN
          DELETE FROM value_integer_ext WHERE id = ext_value_integer_id(OLD.id);
        ELSE
          DELETE FROM value_choice_ext WHERE id = ext_integer_value_choice_id(OLD.id);
        END IF;
      WHEN 'TRUNCATE' THEN
        TRUNCATE value_integer_ext;
        -- how to truncate value_choice?!?
      WHEN 'UPDATE' THEN

        IF NEW.value IS NOT NULL THEN
          IF NEW.choice_id IS NULL THEN
            UPDATE value_integer_ext
            SET entity_id = ext_entity_id(NEW.entity_id)
              , attribute_id = ext_attribute_id(NEW.attribute_id)
              , value = NEW.value
              , create_date = NEW.create_date
              , create_user_id = ext_user_id(NEW.create_user_id)
              , modify_date = NEW.modify_date
              , modify_user_id = ext_user_id(NEW.modify_user_id)
              , revision = NEW.revision
            WHERE id = ext_value_integer_id(OLD.id)
          ELSE
            UPDATE value_choice_ext
            SET entity_id = ext_entity_id(NEW.entity_id)
              , attribute_id = ext_attribute_id(NEW.attribute_id)
              , value = ext_choice_id(NEW.choice_id)
              , create_date = NEW.create_date
              , create_user_id = ext_user_id(NEW.create_user_id)
              , modify_date = NEW.modify_date
              , modify_user_id = ext_user_id(NEW.modify_user_id)
              , revision = NEW.revision
            WHERE id = ext_integer_value_choice_id(OLD.id)
          END IF;
        END IF;

    END CASE;
    RETURN NULL;
  END;
$value_integer_mirror$ LANGUAGE plpgsql;


CREATE TRIGGER value_integer_mirror AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE ON value_integer
  FOR EACH ROW EXECUTE PROCEDURE value_integer_mirror();
