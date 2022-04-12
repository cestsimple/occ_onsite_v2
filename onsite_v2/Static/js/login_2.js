let vm = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        loginForm: {
            username: '',
            password: '',
        }

    },
    mounted() {
    },
    methods: {
        fnLogin(){
            this.$refs.loginFormRef.resetFields();
        },
        fnClear(){

        }
    }
});