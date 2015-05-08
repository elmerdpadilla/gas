//Definimos el modulo web de Odoo como una funcion de openerp
//El nombre de la funcion debe ser el mismo que la del modulo(tienda_mascota)
openerp.tienda_mascota = function(instance, local) {
    //Traduccion
    var _t = instance.web._t,
       _lt = instance.web._lt;
var c;
var ctx
    //Qweb
    var QWeb = instance.web.qweb;
    //Construimos un widget basico de nombre PaginaPrincipal
    local.PaginaPrincipal = instance.Widget.extend({
        start: function() {
            //Agregando el template(HomePageTemplate) definida en tienda_mascota/static/src/xml/tienda_mascota.xml a la PaginaPrincipal
            //QWeb.render() busca la plantilla a mostrar
            this.$el.append(QWeb.render("HomePageTemplate")); 
  console.log('START');  
$('button#bstart').click(this.myfunction);  //link button to function  
c = document.getElementById("myCanvas");
ctx = c.getContext("2d");
            },   
        myfunction: function() {
ctx.fillStyle = "#BFFF00";
ctx.fillRect(0,0,150,75);
alert("hola ");
        },         
    });
    //Registra nuestro widget básico como una acción cliente que sera llamado desde la accion creado en  tienda_mascota/tienda_mascota.xml
    instance.web.client_actions.add('tienda_mascota.paginainicio', 'instance.tienda_mascota.PaginaPrincipal');

}
