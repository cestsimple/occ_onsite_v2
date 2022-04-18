let vm = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],
    data: {
        is_show_edit: false,
        form_apsa: {
            id: 0,
            asset:{
                confirm: 0,
                id: 0,
                name: '',
                site:{
                    id: 0,
                    cname: '',
                    ename: '',
                    engineer: {
                        id: 0,
                        region: '',
                        mtgroup: '',
                        name: '',
                    }
                }
            },
            onsite_type: '',
            onsite_series: '',
            facility_fin: '',
            daily_js: 0,
            temperature: 0,
            vap_max: '',
            vap_type: '',
            norminal_flow: 0,
            daily_bind: '',
            flow_meter: '',
            cooling_fixed: 0,
            comment: '',
            asset: 0,
        },
        form_variables: [],

        error_flag: false,
        default_address_id: '',

        //资产列表
        apsa: [],
        edit_apsa_index: '',
    },
    mounted() {
        // 获取省份数据
        this.get_apsa();
    },
    methods: {
        // 展示编辑地址弹框
        show_edit_site(index){
            this.is_show_edit = true;
            // 只获取要编辑的数据
            this.form_apsa = JSON.parse(JSON.stringify(this.apsa[index]))
            console.log(this.form_apsa)
        },
        // 获取apsa数据
        get_apsa(){
            let url = '/apsa/';
            axios.get(url, {
                responseType: 'json',
                 headers: {
                        'authorization': 'JWT ' + localStorage.token
                    }
            })
                .then(response => {
                    this.apsa = JSON.parse(JSON.stringify(response.data));
                    console.log(this.apsa)
                })
                .catch(error => {
                    console.log(error.response.data)
                    if (error.response.status == 401){
                        top.location.href = '/user/login/';
                        return
                    }
                    console.log(error.response);
                    this.assets = [];
                })

        },
        // 新增地址
        save_asset(){
            if (this.error_flag) {
                alert('信息填写有误！');
            } else {
                // 注意：0 == '';返回true; 0 === '';返回false;
                if (this.editing_address_index === '') {
                    // 新增地址
                    let url = '/addresses/create/';
                    axios.post(url, this.form_address, {
                        headers: {
                            'X-CSRFToken':getCookie('csrftoken')
                        },
                        responseType: 'json'
                    })
                        .then(response => {
                            if (response.data.code == '0') {
                                // 局部刷新界面：展示所有地址信息，将新的地址添加到头部
                                this.addresses.splice(0, 0, response.data.address);
                                this.is_show_edit = false;
                            } else if (response.data.code == '4101') {
                                location.href = '/login/?next=/addresses/';
                            } else {
                                alert(response.data.errmsg);
                            }
                        })
                        .catch(error => {
                            console.log(error.response);
                        })
                } else {
                    // 修改地址
                    let url = '/addresses/' + this.addresses[this.editing_address_index].id + '/';
                    axios.put(url, this.form_address, {
                        headers: {
                            'X-CSRFToken':getCookie('csrftoken')
                        },
                        responseType: 'json'
                    })
                        .then(response => {
                            if (response.data.code == '0') {
                                this.addresses[this.editing_address_index] = response.data.address;
                                this.is_show_edit = false;
                            } else if (response.data.code == '4101') {
                                location.href = '/login/?next=/addresses/';
                            } else {
                                alert(response.data.errmsg);
                            }
                        })
                        .catch(error => {
                            alert(error.response);
                        })
                }
            }
        },
    }
});