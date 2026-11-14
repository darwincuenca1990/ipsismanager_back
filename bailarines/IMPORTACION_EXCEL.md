# Importación de bailarines desde Excel

`POST /api/bailarines/importar-excel/` recibe `multipart/form-data` con un archivo
`.xlsx` en el campo `archivo`. Requiere el permiso de creación de bailarines.

Se procesa la primera hoja, con encabezados en la fila 2 y registros desde la
fila 3. Se reconocen los encabezados del template de cumpleaños, sin distinguir
mayúsculas ni tildes. Las columnas obligatorias son cédula, apellidos, nombres,
fecha de nacimiento, elenco, fecha de ingreso, estado y representante. El
representante debe ser Padre o Madre y debe tener nombres, apellidos y celular
en las columnas correspondientes.

Cada fila crea un grupo familiar independiente, un bailarín y su inscripción.
Las validaciones habituales se aplican, incluida la obligación de proporcionar
institución educativa cuando estudia y lugar de trabajo cuando trabaja. No se
importan fotografías ni autorizaciones de publicación. La cédula y el celular
deben guardarse como texto en Excel para preservar los ceros iniciales.

La respuesta contiene `creados` (número de fila e ID) y `errores` (número de
fila y detalles). Cada fila se procesa por separado: las válidas se guardan y
las inválidas se omiten, sin crear grupos familiares huérfanos. Una cédula ya
registrada se informa como error; la importación no modifica bailarines existentes.
