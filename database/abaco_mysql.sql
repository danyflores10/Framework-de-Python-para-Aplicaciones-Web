-- =====================================================================
-- Base de datos «abaco» para MySQL / MariaDB
-- Proyecto: Ábaco - Gestión de Cursos con Flask
--
-- Formas de uso:
--   1) phpMyAdmin (XAMPP): pestaña «Importar» y seleccionar este archivo.
--   2) Consola:   mysql -u root -p < database/abaco_mysql.sql
--   3) Flask CLI: flask --app app/app.py init-db   (con DB_MOTOR=mysql)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS abaco
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE abaco;

DROP TABLE IF EXISTS curso;

CREATE TABLE curso (
  codigo          CHAR(6)          NOT NULL,
  nombre          VARCHAR(80)      NOT NULL,
  creditos        TINYINT UNSIGNED NOT NULL,
  docente         VARCHAR(80)      NOT NULL,
  modalidad       VARCHAR(15)      NOT NULL DEFAULT 'Presencial',
  descripcion     VARCHAR(500)     NULL,
  fecha_registro  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pk_curso PRIMARY KEY (codigo),
  CONSTRAINT chk_curso_creditos CHECK (creditos BETWEEN 1 AND 10),
  CONSTRAINT chk_curso_modalidad CHECK (modalidad IN ('Presencial', 'Virtual', 'Híbrida'))
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

INSERT INTO curso (codigo, nombre, creditos, docente, modalidad, descripcion) VALUES
('PRG101', 'Introducción a la Programación con Python', 4, 'Ana Torres Rivas', 'Presencial',
 'Fundamentos de algoritmia, variables, estructuras de control y funciones con Python 3.'),
('PRG102', 'Programación Orientada a Objetos con Java', 4, 'Carlos Mendoza Paz', 'Presencial',
 'Clases, objetos, herencia, polimorfismo e interfaces aplicados en proyectos con Java.'),
('WEB201', 'Desarrollo Web con Flask', 4, 'Lucía Ramírez Soto', 'Híbrida',
 'Construcción de aplicaciones web con el microframework Flask, Jinja2 y bases de datos.'),
('WEB202', 'Desarrollo Web con PHP y MySQL', 3, 'Jorge Salazar Vega', 'Virtual',
 'Programación del lado del servidor con PHP y persistencia de datos en MySQL.'),
('WEB203', 'JavaScript Moderno', 3, 'María Fernández Gil', 'Virtual',
 'ECMAScript actual, manipulación del DOM, módulos y consumo de API con fetch.'),
('MOV301', 'Desarrollo Móvil con Kotlin', 4, 'Diego Vargas León', 'Presencial',
 'Aplicaciones nativas para Android con Kotlin y buenas prácticas de arquitectura.'),
('MOV302', 'Aplicaciones Multiplataforma con Dart y Flutter', 4, 'Rosa Quispe Huamán', 'Híbrida',
 'Desarrollo de interfaces multiplataforma con los widgets de Flutter y el lenguaje Dart.'),
('BDA201', 'Bases de Datos Relacionales', 4, 'Luis Paredes Castro', 'Presencial',
 'Modelo entidad-relación, normalización y consultas SQL en MySQL y MariaDB.'),
('ALG201', 'Algoritmos y Estructuras de Datos', 5, 'Ana Torres Rivas', 'Presencial',
 'Análisis de complejidad, listas, pilas, colas, árboles, grafos y algoritmos de ordenamiento.'),
('ING301', 'Ingeniería de Software', 3, 'Carlos Mendoza Paz', 'Híbrida',
 'Ciclo de vida del software, requerimientos, diseño, pruebas y metodologías ágiles.'),
('RED301', 'Redes de Computadoras', 3, 'Jorge Salazar Vega', 'Presencial',
 'Modelo TCP/IP, protocolos de aplicación como HTTP y configuración básica de redes.'),
('SEG401', 'Seguridad en Aplicaciones Web', 3, 'Lucía Ramírez Soto', 'Virtual',
 'Principales riesgos del OWASP Top 10 y técnicas de protección como tokens CSRF y hashing.');

-- Consulta utilizada en el video para comprobar los datos:
-- SELECT codigo, nombre, creditos FROM curso ORDER BY nombre ASC;
